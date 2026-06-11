# /deploy/kubeflow/MLOps-Example/kubeflow_pipeline/pipeline.py
import kfp
from kfp import dsl, compiler
from kfp import kubernetes

# 컴포넌트 정의
@dsl.component(base_image="qorehd222/mnist-pre-data:latest")
def load_preprocess_data(): pass

@dsl.component(base_image="qorehd222/mnist-val-data:latest")
def validate_data(): pass

@dsl.component(base_image="qorehd222/mnist-train-model:latest")
def train_model(): pass

@dsl.component(base_image="qorehd222/mnist-embedding:latest")
def embedding(): pass

@dsl.component(base_image="qorehd222/mnist-train-faiss:latest")
def train_faiss(): pass

@dsl.component(base_image="qorehd222/mnist-analysis:latest")
def analysis(manage_url: str) -> float:
    return 0.0

@dsl.component(base_image="qorehd222/mnist-deploy:latest")
def deploy_model(manage_url: str): pass


@dsl.pipeline(name="mnist using arcface", description="CT pipeline")
def mnist_pipeline():
    MANAGE_URL = 'http://220.116.228.93:8088/send'

    t0 = load_preprocess_data()
    t0.set_display_name('collect & preprocess data')
    kubernetes.mount_pvc(t0, pvc_name='data-pvc', mount_path='/data')

    t1 = validate_data().after(t0)
    t1.set_display_name('validate data')
    kubernetes.mount_pvc(t1, pvc_name='data-pvc', mount_path='/data')

    t2 = train_model().after(t1)
    t2.set_display_name('train model')
    kubernetes.mount_pvc(t2, pvc_name='data-pvc', mount_path='/data')
    kubernetes.mount_pvc(t2, pvc_name='train-model-pvc', mount_path='/model')

    t3 = embedding().after(t2)
    t3.set_display_name('embedding')
    kubernetes.mount_pvc(t3, pvc_name='data-pvc', mount_path='/data')
    kubernetes.mount_pvc(t3, pvc_name='train-model-pvc', mount_path='/model')

    t4 = train_faiss().after(t3)
    t4.set_display_name('train faiss')
    kubernetes.mount_pvc(t4, pvc_name='data-pvc', mount_path='/data')
    kubernetes.mount_pvc(t4, pvc_name='train-model-pvc', mount_path='/model')

    t5 = analysis(manage_url=MANAGE_URL).after(t4)
    t5.set_display_name('analysis')
    kubernetes.mount_pvc(t5, pvc_name='data-pvc', mount_path='/data')
    kubernetes.mount_pvc(t5, pvc_name='train-model-pvc', mount_path='/model')

    with dsl.If(t5.output > 0.8):
        t6 = deploy_model(manage_url=MANAGE_URL).after(t5)
        t6.set_display_name('deploy')
        kubernetes.mount_pvc(t6, pvc_name='train-model-pvc', mount_path='/model')
        kubernetes.mount_pvc(t6, pvc_name='deploy-model-pvc', mount_path='/deploy-model')


if __name__ == "__main__":
    host = "http://192.168.3.186:80"   # Istio ingress (포트포워드 중인 주소)
    namespace = "kubeflow-user-example-com"

    pipeline_name = "Mnist"
    pipeline_package_path = "pipeline.yaml"  # 2.x는 yaml
    version = "v0.2"
    experiment_name = "For Develop"
    run_name = "kubeflow study {}".format(version)

    # 컴파일
    compiler.Compiler().compile(mnist_pipeline, pipeline_package_path)

    # 클라이언트 연결
    client = kfp.Client(host=host, namespace=namespace)

    # 파이프라인 업로드
    pipeline_id = client.get_pipeline_id(pipeline_name)
    if pipeline_id:
        client.upload_pipeline_version(
            pipeline_package_path=pipeline_package_path,
            pipeline_version_name=version,
            pipeline_id=pipeline_id
        )
    else:
        pipeline = client.upload_pipeline(
            pipeline_package_path=pipeline_package_path,
            pipeline_name=pipeline_name
        )
        pipeline_id = pipeline.pipeline_id

    # 실험 및 실행
    experiment = client.create_experiment(
        name=experiment_name,
        namespace=namespace
    )
    run = client.create_run_from_pipeline_package(
        pipeline_file=pipeline_package_path,
        arguments={},
        run_name=run_name,
        experiment_name=experiment_name,
        namespace=namespace
    )
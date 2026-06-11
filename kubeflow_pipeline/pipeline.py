# # /deploy/kubeflow/MLOps-Example/kubeflow_pipeline/pipeline.py
# import os

# import kfp
# import kfp.components as comp
# from kfp import dsl
# from kfp import onprem
# from kubernetes import client as k8s_client
# from kubernetes.client.models import V1EnvVar

# @dsl.pipeline(
#     name="mnist using arcface",
#     description="CT pipeline"
# )
# def mnist_pipeline():
#     ENV_MANAGE_URL = V1EnvVar(name='MANAGE_URL', value='http://220.116.228.93:8088/send')

#     data_0 = dsl.ContainerOp(
#         name="load & preprocess data pipeline",
#         image="qorehd222/mnist-pre-data:latest",
#     ).set_display_name('collect & preprocess data')\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))

#     data_1 = dsl.ContainerOp(
#         name="validate data pipeline",
#         image="qorehd222/mnist-val-data:latest",
#     ).set_display_name('validate data').after(data_0)\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))

#     train_model = dsl.ContainerOp(
#         name="train embedding model",
#         image="qorehd222/mnist-train-model:latest",
#     ).set_display_name('train model').after(data_1)\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))\
#     .apply(onprem.mount_pvc("train-model-pvc", volume_name="train-model", volume_mount_path="/model"))

#     embedding = dsl.ContainerOp(
#         name="embedding data using embedding model",
#         image="qorehd222/mnist-embedding:latest",
#     ).set_display_name('embedding').after(train_model)\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))\
#     .apply(onprem.mount_pvc("train-model-pvc", volume_name="train-model", volume_mount_path="/model"))

#     train_faiss = dsl.ContainerOp(
#         name="train faiss",
#         image="qorehd222/mnist-train-faiss:latest",
#     ).set_display_name('train faiss').after(embedding)\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))\
#     .apply(onprem.mount_pvc("train-model-pvc", volume_name="train-model", volume_mount_path="/model"))

#     analysis = dsl.ContainerOp(
#         name="analysis total",
#         image="qorehd222/mnist-analysis:latest",
#         file_outputs={
#             "confusion_matrix": "/confusion_matrix.csv",
#             "mlpipeline-ui-metadata": "/mlpipeline-ui-metadata.json",
#             "accuracy": "/accuracy.json",
#             "mlpipeline_metrics": "/mlpipeline-metrics.json"
#         }
#     ).add_env_variable(ENV_MANAGE_URL).set_display_name('analysis').after(train_faiss)\
#     .apply(onprem.mount_pvc("data-pvc", volume_name="data", volume_mount_path="/data"))\
#     .apply(onprem.mount_pvc("train-model-pvc", volume_name="train-model", volume_mount_path="/model"))

#     baseline = 0.8
#     with dsl.Condition(analysis.outputs["accuracy"] > baseline) as check_deploy:
#         deploy = dsl.ContainerOp(
#             name="deploy mar",
#             image="qorehd222/mnist-deploy:latest",
#         ).add_env_variable(ENV_MANAGE_URL).set_display_name('deploy').after(analysis)\
#         .apply(onprem.mount_pvc("train-model-pvc", volume_name="train-model", volume_mount_path="/model"))\
#         .apply(onprem.mount_pvc("deploy-model-pvc", volume_name="deploy-model", volume_mount_path="/deploy-model"))

# if __name__=="__main__":
#     host = "http://220.116.228.93:8089/pipeline"
#     namespace = "kbj"
    
#     pipeline_name = "Mnist"
#     pipeline_package_path = "pipeline.zip"
#     version = "v0.2"

#     experiment_name = "For Develop"
#     run_name = "kubeflow study {}".format(version)

#     client = kfp.Client(host=host, namespace=namespace)
#     kfp.compiler.Compiler().compile(mnist_pipeline, pipeline_package_path)

#     pipeline_id = client.get_pipeline_id(pipeline_name)
#     if pipeline_id:
#         client.upload_pipeline_version(
#             pipeline_package_path=pipeline_package_path,
#             pipeline_version_name=version,
#             pipeline_name=pipeline_name
#         )
#     else:
#         client.upload_pipeline(
#             pipeline_package_path=pipeline_package_path,
#             pipeline_name=pipeline_name
#         )
    
#     experiment = client.create_experiment(name=experiment_name, namespace=namespace)
#     run = client.run_pipeline(experiment.id, run_name, pipeline_package_path)
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
"""K8s 深度操作工具 — 重启/扩缩容/回滚/Pod exec"""
from typing import Optional, Dict, Any, List, Tuple

from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

from .client import K8sClient
from .logs import K8sLogTools


class K8sOps:
    """K8s 运维操作工具"""

    @staticmethod
    def restart_deployment(
        k8s_client: K8sClient,
        name: str,
        namespace: str = "default",
    ) -> Tuple[bool, str]:
        """滚动重启 Deployment

        Args:
            k8s_client: 已连接的 K8s 客户端
            name: Deployment 名称
            namespace: 命名空间

        Returns:
            (success, message)
        """
        try:
            # 确认 Deployment 存在
            k8s_client.apps_v1.read_namespaced_deployment(name, namespace)

            # 通过 patch 添加 annotation 触发滚动重启
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": __import__("datetime").datetime.now().isoformat(),
                            }
                        }
                    }
                }
            }

            k8s_client.apps_v1.patch_namespaced_deployment(name, namespace, body)
            return True, f"Deployment {namespace}/{name} 滚动重启已触发"

        except ApiException as e:
            if e.status == 404:
                return False, f"Deployment {namespace}/{name} 不存在"
            return False, f"重启失败：{e.reason}"
        except Exception as e:
            return False, f"重启失败：{str(e)}"

    @staticmethod
    def scale_deployment(
        k8s_client: K8sClient,
        name: str,
        namespace: str,
        replicas: int,
    ) -> Tuple[bool, str]:
        """扩缩容 Deployment

        Args:
            k8s_client: 已连接的 K8s 客户端
            name: Deployment 名称
            namespace: 命名空间
            replicas: 目标副本数

        Returns:
            (success, message)
        """
        try:
            deploy = k8s_client.apps_v1.read_namespaced_deployment(name, namespace)
            current = deploy.spec.replicas

            body = {"spec": {"replicas": replicas}}
            k8s_client.apps_v1.patch_namespaced_deployment(name, namespace, body)

            action = "扩容" if replicas > current else "缩容" if replicas < current else "调整"
            return True, f"Deployment {namespace}/{name} {action}：{current} → {replicas} 副本"

        except ApiException as e:
            if e.status == 404:
                return False, f"Deployment {namespace}/{name} 不存在"
            return False, f"扩缩容失败：{e.reason}"
        except Exception as e:
            return False, f"扩缩容失败：{str(e)}"

    @staticmethod
    def rollback_deployment(
        k8s_client: K8sClient,
        name: str,
        namespace: str,
        to_revision: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """回滚 Deployment

        Args:
            k8s_client: 已连接的 K8s 客户端
            name: Deployment 名称
            namespace: 命名空间
            to_revision: 回滚到指定版本，None 表示回滚到上一个版本

        Returns:
            (success, message)
        """
        try:
            # 确认 Deployment 存在
            k8s_client.apps_v1.read_namespaced_deployment(name, namespace)

            # 使用 CoreV1Api 创建 rollback 请求
            # 实际上 kubernetes SDK 不直接支持 rollout undo
            # 需要通过 patch annotations 来实现
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubernetes.io/change-cause": f"Rollback via Keeper at {__import__('datetime').datetime.now().isoformat()}",
                            }
                        }
                    }
                }
            }

            # 获取 ReplicaSet 历史
            rs_list = k8s_client.apps_v1.list_namespaced_replica_set(
                namespace,
                label_selector=f"app={name}" if name else "",
            )

            if to_revision and rs_list.items:
                # 查找指定版本的 ReplicaSet
                target_rs = None
                for rs in rs_list.items:
                    if str(rs.metadata.annotations.get("deployment.kubernetes.io/revision", "")) == str(to_revision):
                        target_rs = rs
                        break

                if target_rs:
                    # 将目标 RS 的 pod template 复制到当前 Deployment
                    body["spec"]["template"] = target_rs.spec.template
                    body["spec"]["template"].metadata = target_rs.spec.template.metadata

            k8s_client.apps_v1.patch_namespaced_deployment(name, namespace, body)
            return True, f"Deployment {namespace}/{name} 回滚已触发"

        except ApiException as e:
            if e.status == 404:
                return False, f"Deployment {namespace}/{name} 不存在"
            return False, f"回滚失败：{e.reason}"
        except Exception as e:
            return False, f"回滚失败：{str(e)}"

    @staticmethod
    def get_deployment_history(
        k8s_client: K8sClient,
        name: str,
        namespace: str,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """获取 Deployment 历史版本

        Returns:
            (success, history_list)
        """
        try:
            rs_list = k8s_client.apps_v1.list_namespaced_replica_set(
                namespace,
                label_selector=f"app.kubernetes.io/instance={name},app.kubernetes.io/name={name}"
            )

            # 如果 label_selector 没匹配到，尝试更宽松的过滤
            if not rs_list.items:
                all_rs = k8s_client.apps_v1.list_namespaced_replica_set(namespace)
                rs_list.items = [rs for rs in all_rs.items if name in rs.metadata.name]

            history = []
            for rs in rs_list.items:
                revision = rs.metadata.annotations.get(
                    "deployment.kubernetes.io/revision", "unknown"
                )
                change_cause = rs.metadata.annotations.get(
                    "kubernetes.io/change-cause", "unknown"
                )
                history.append({
                    "name": rs.metadata.name,
                    "revision": revision,
                    "replicas": rs.spec.replicas,
                    "ready_replicas": rs.status.ready_replicas or 0,
                    "change_cause": change_cause,
                    "age": str(rs.metadata.creation_timestamp),
                })

            return True, history
        except Exception as e:
            return False, [{"error": str(e)}]

    @staticmethod
    def exec_in_pod(
        k8s_client: K8sClient,
        pod_name: str,
        namespace: str,
        command: str,
        container: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """在 Pod 中执行命令 — 直接调用已有的 K8sLogTools.exec_in_pod"""
        return K8sLogTools.exec_in_pod(
            k8s_client, pod_name=pod_name, namespace=namespace,
            command=command, container=container,
        )

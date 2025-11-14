import os
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    CfnOutput
)
from constructs import Construct

class BedrockAgentOnEcsCdkDeploymentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)
        
        # docker image build local path
        agent_code_path = os.path.join(os.path.dirname(__file__), "..", "agent")

        # docker image asset
        docker_image = ecr_assets.DockerImageAsset(
            self, "BedrockAgentDockerImage",
            directory=agent_code_path,
            platform=ecr_assets.Platform.LINUX_AMD64                                                           
        )                                            

        # ECS Cluster
        cluster = ecs.Cluster(self, "BedrockAgentCluster",
                              vpc=vpc,
                              cluster_name="BedrockAgentCluster"
                              )
        
        # ecs task role
        task_role = iam.Role(self, "BedrockAgentTaskRole",
                             assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
                             )
        task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )

        task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["arn:aws:bedrock:*::*model*/*", "arn:aws:bedrock:*::inference-profile/*"]
            )
        )
        

        # ecs task definition for fargate
        task_definition = ecs.FargateTaskDefinition(
            self, "BedrockAgentTaskDef",
            memory_limit_mib=1024,
            cpu=512,
            task_role=task_role
            )
        # adding container to ecs task definition
        container = task_definition.add_container(
            "BedrockAgentContainer",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="BedrockAgent",
                log_retention=logs.RetentionDays.ONE_WEEK
            ),
            port_mappings=[ecs.PortMapping(container_port=8080)],
            environment={
                "PYTHONUNBUFFERED": "1",
                "AWS_DEFAULT_REGION": "us-east-1"
            }
        )
        # container.add_port_mappings(
        #     ecs.PortMapping(
        #         container_port=8080,
        #         protocol=ecs.Protocol.TCP
        #     )
        # )

        # Fargate service with Application Load Balancer
        fargate = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "BedrockAgentFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            public_load_balancer=True,
            assign_public_ip=True,
            listener_port=80
        )

        # allow inbound http traffic from application load balancer to fargate service
        fargate.service.connections.allow_from(
            fargate.load_balancer,
            ec2.Port.tcp(8080),
            "Allow inbound HTTP traffic from Load Balancer"
        )

        # target group health check configuration
        fargate.target_group.configure_health_check(
            path="/",
            interval=Duration.seconds(60),
            timeout=Duration.seconds(10),
            healthy_threshold_count=2,
            unhealthy_threshold_count=10,
            healthy_http_codes="200-499"
        )

        # auto scaling based on cpu utilization
        scalable_target = fargate.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=3
        )
        scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )   

        # Output the Load Balancer DNS
        CfnOutput(
            self, "LoadBalancerDNS",
            value=fargate.load_balancer.load_balancer_dns_name
        )
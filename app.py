#!/usr/bin/env python3
import os

import aws_cdk as cdk

from bedrock_agent_on_ecs_cdk_deployment.bedrock_agent_on_ecs_cdk_deployment_stack import BedrockAgentOnEcsCdkDeploymentStack


app = cdk.App()
BedrockAgentOnEcsCdkDeploymentStack(app, "BedrockAgentOnEcsCdkDeploymentStack",
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)
    )

app.synth()

resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ── CloudWatch log groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "services" {
  for_each          = toset(["tracker", "node-a", "node-b"])
  name              = "/ecs/${var.app_name}/${each.key}"
  retention_in_days = 7
}

# ── AWS Cloud Map (internal DNS for service-to-service calls) ─────────────────

resource "aws_service_discovery_private_dns_namespace" "lumina" {
  name = "lumina.local"
  vpc  = aws_vpc.main.id
}

resource "aws_service_discovery_service" "tracker" {
  name = "tracker"

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.lumina.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_service_discovery_service" "node_b" {
  name = "node-b"

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.lumina.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ── Tracker task + service ────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "tracker" {
  family                   = "${var.app_name}-tracker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.tracker_cpu
  memory                   = var.tracker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "tracker"
    image     = "${aws_ecr_repository.services["tracker"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8003
      protocol      = "tcp"
    }]

    environment = [
      { name = "SPLIT_LAYER",            value = tostring(var.split_layer) },
      { name = "HEARTBEAT_TIMEOUT_SEC",  value = tostring(var.heartbeat_timeout_sec) },
    ]

    command = ["uvicorn", "tracker:app", "--host", "0.0.0.0", "--port", "8003"]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["tracker"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "tracker" {
  name                   = "${var.app_name}-tracker"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.tracker.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.tracker.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.tracker.arn
  }
}

# ── Node B task + service ─────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "node_b" {
  family                   = "${var.app_name}-node-b"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.node_cpu
  memory                   = var.node_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "node-b"
    image     = "${aws_ecr_repository.services["node-b"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8002
      protocol      = "tcp"
    }]

    environment = [
      { name = "MODEL_NAME",           value = var.model_name },
      { name = "SPLIT_LAYER",          value = tostring(var.split_layer) },
      { name = "TRACKER_URL",          value = "http://tracker.lumina.local:8003" },
      { name = "ENABLE_DYNAMIC_SPLIT", value = tostring(var.enable_dynamic_split) },
      { name = "NODE_B_ID",            value = "node-b" },
    ]

    command = ["uvicorn", "node_b:app", "--host", "0.0.0.0", "--port", "8002"]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["node-b"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "node_b" {
  name                   = "${var.app_name}-node-b"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.node_b.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.node_b.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.node_b.arn
  }

  depends_on = [aws_ecs_service.tracker]
}

# ── Node A task + service ─────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "node_a" {
  family                   = "${var.app_name}-node-a"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.node_cpu
  memory                   = var.node_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "node-a"
    image     = "${aws_ecr_repository.services["node-a"].repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8001
      protocol      = "tcp"
    }]

    environment = [
      { name = "MODEL_NAME",           value = var.model_name },
      { name = "SPLIT_LAYER",          value = tostring(var.split_layer) },
      { name = "NODE_B_URL",           value = "http://node-b.lumina.local:8002" },
      { name = "TRACKER_URL",          value = "http://tracker.lumina.local:8003" },
      { name = "ENABLE_DYNAMIC_SPLIT", value = tostring(var.enable_dynamic_split) },
      { name = "NODE_A_ID",            value = "node-a" },
    ]

    command = ["uvicorn", "node_a:app", "--host", "0.0.0.0", "--port", "8001"]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.services["node-a"].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "node_a" {
  name                   = "${var.app_name}-node-a"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.node_a.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.node_a.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.node_a.arn
    container_name   = "node-a"
    container_port   = 8001
  }

  depends_on = [
    aws_ecs_service.tracker,
    aws_ecs_service.node_b,
    aws_lb_listener.http,
  ]
}

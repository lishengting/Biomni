#!/bin/bash

# Biomni Docker 部署脚本
# 用于快速部署和管理Biomni环境

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}Biomni Docker 部署脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  basic     - 部署基础环境（快速启动，仅AI代理功能）"
    echo "  full      - 部署完整环境（包含所有生物信息学工具）"
    echo "  dev       - 部署开发环境（挂载源代码）"
    echo "  build     - 仅构建镜像，不启动容器"
    echo "  stop      - 停止所有容器"
    echo "  clean     - 清理所有容器和镜像"
    echo "  logs      - 查看容器日志"
    echo "  shell     - 进入容器shell"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 basic    # 启动基础环境"
    echo "  $0 full     # 启动完整环境"
    echo "  $0 stop     # 停止所有容器"
}

# 创建必要的目录
create_directories() {
    echo -e "${YELLOW}创建必要的目录...${NC}"
    mkdir -p data notebooks results
    echo -e "${GREEN}目录创建完成！${NC}"
}

# 构建镜像
build_image() {
    local profile=$1
    echo -e "${YELLOW}构建 $profile 环境镜像...${NC}"
    
    case $profile in
        "basic")
            docker-compose --profile basic build biomni-basic
            ;;
        "full")
            docker-compose --profile full build biomni-full
            ;;
        "dev")
            docker-compose --profile dev build biomni-dev
            ;;
        *)
            echo -e "${RED}未知的环境类型: $profile${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}镜像构建完成！${NC}"
}

# 启动服务
start_service() {
    local profile=$1
    echo -e "${YELLOW}启动 $profile 环境...${NC}"
    
    create_directories
    
    case $profile in
        "basic")
            docker-compose --profile basic up -d biomni-basic
            echo -e "${GREEN}基础环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://localhost:8888${NC}"
            echo -e "${BLUE}Gradio: http://localhost:7860${NC}"
            ;;
        "full")
            docker-compose --profile full up -d biomni-full
            echo -e "${GREEN}完整环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://localhost:8889${NC}"
            echo -e "${BLUE}Gradio: http://localhost:7861${NC}"
            ;;
        "dev")
            docker-compose --profile dev up -d biomni-dev
            echo -e "${GREEN}开发环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://localhost:8890${NC}"
            echo -e "${BLUE}Gradio: http://localhost:7862${NC}"
            ;;
        *)
            echo -e "${RED}未知的环境类型: $profile${NC}"
            exit 1
            ;;
    esac
}

# 停止所有容器
stop_containers() {
    echo -e "${YELLOW}停止所有Biomni容器...${NC}"
    docker-compose down
    echo -e "${GREEN}所有容器已停止！${NC}"
}

# 清理所有容器和镜像
clean_all() {
    echo -e "${YELLOW}清理所有Biomni容器和镜像...${NC}"
    docker-compose down --rmi all --volumes --remove-orphans
    echo -e "${GREEN}清理完成！${NC}"
}

# 查看容器日志
show_logs() {
    local profile=$1
    case $profile in
        "basic")
            docker-compose --profile basic logs -f biomni-basic
            ;;
        "full")
            docker-compose --profile full logs -f biomni-full
            ;;
        "dev")
            docker-compose --profile dev logs -f biomni-dev
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
            exit 1
            ;;
    esac
}

# 进入容器shell
enter_shell() {
    local profile=$1
    case $profile in
        "basic")
            docker-compose --profile basic exec biomni-basic /bin/bash
            ;;
        "full")
            docker-compose --profile full exec biomni-full /bin/bash
            ;;
        "dev")
            docker-compose --profile dev exec biomni-dev /bin/bash
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
            exit 1
            ;;
    esac
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker未安装！${NC}"
        echo "请先安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: Docker Compose未安装！${NC}"
        echo "请先安装Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# 主函数
main() {
    check_docker
    
    case $1 in
        "basic")
            start_service "basic"
            ;;
        "full")
            start_service "full"
            ;;
        "dev")
            start_service "dev"
            ;;
        "build")
            if [ -z "$2" ]; then
                echo -e "${RED}请指定要构建的环境: basic, full, 或 dev${NC}"
                exit 1
            fi
            build_image "$2"
            ;;
        "stop")
            stop_containers
            ;;
        "clean")
            clean_all
            ;;
        "logs")
            if [ -z "$2" ]; then
                echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
                exit 1
            fi
            show_logs "$2"
            ;;
        "shell")
            if [ -z "$2" ]; then
                echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
                exit 1
            fi
            enter_shell "$2"
            ;;
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 
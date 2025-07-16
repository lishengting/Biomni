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
    echo "用法: $0 [选项] [环境类型]"
    echo ""
    echo "选项:"
    echo "  basic     - 部署基础环境（快速启动，仅AI代理功能）"
    echo "  full      - 部署完整环境（包含所有生物信息学工具）"
    echo "  dev       - 部署开发环境（挂载源代码）"
    echo "  build     - 仅构建镜像，不启动容器"
    echo "  stop      - 停止容器 (支持: basic, full, dev, all)"
    echo "  clean     - 清理容器和镜像 (支持: basic, full, dev, all)"
    echo "  logs      - 查看容器日志"
    echo "  shell     - 进入容器shell"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "全局选项:"
    echo "  -p        - 构建时使用 --progress=plain 显示详细输出"
    echo ""
    echo "示例:"
    echo "  $0 basic           # 启动基础环境"
    echo "  $0 full            # 启动完整环境"
    echo "  $0 -p build full   # 构建完整环境并显示详细输出"
    echo "  $0 stop basic      # 停止基础环境"
    echo "  $0 stop all        # 停止所有环境"
    echo "  $0 clean full      # 清理完整环境"
    echo "  $0 clean all       # 清理所有环境"
    echo "  $0 logs full       # 查看完整环境日志"
    echo "  $0 shell dev       # 进入开发环境shell"
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
    local progress_flag=$2
    echo -e "${YELLOW}构建 $profile 环境镜像...${NC}"
    
    case $profile in
        "basic")
            docker compose --profile basic build $progress_flag biomni-basic
            ;;
        "full")
            docker compose --profile full build $progress_flag biomni-full
            ;;
        "dev")
            docker compose --profile dev build $progress_flag biomni-dev
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
            docker compose --profile basic up -d biomni-basic
            echo -e "${GREEN}基础环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8888${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7860${NC}"
            ;;
        "full")
            docker compose --profile full up -d biomni-full
            echo -e "${GREEN}完整环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8889${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7861${NC}"
            ;;
        "dev")
            docker compose --profile dev up -d biomni-dev
            echo -e "${GREEN}开发环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8890${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7862${NC}"
            ;;
        *)
            echo -e "${RED}未知的环境类型: $profile${NC}"
            exit 1
            ;;
    esac
}

# 停止所有容器
stop_containers() {
    local profile=$1
    
    case $profile in
        "basic")
            echo -e "${YELLOW}停止基础环境容器...${NC}"
            docker compose --profile basic down
            echo -e "${GREEN}基础环境容器已停止！${NC}"
            ;;
        "full")
            echo -e "${YELLOW}停止完整环境容器...${NC}"
            docker compose --profile full down
            echo -e "${GREEN}完整环境容器已停止！${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}停止开发环境容器...${NC}"
            docker compose --profile dev down
            echo -e "${GREEN}开发环境容器已停止！${NC}"
            ;;
        "all")
            echo -e "${YELLOW}停止所有Biomni容器...${NC}"
            # 停止所有profile的容器
            docker compose --profile basic down
            docker compose --profile full down
            docker compose --profile dev down
            echo -e "${GREEN}所有容器已停止！${NC}"
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, 或 all${NC}"
            exit 1
            ;;
    esac
}

# 清理所有容器和镜像
clean_all() {
    local profile=$1
    
    case $profile in
        "basic")
            echo -e "${YELLOW}清理基础环境容器和镜像...${NC}"
            docker compose --profile basic down --rmi all --volumes --remove-orphans
            echo -e "${GREEN}基础环境清理完成！${NC}"
            ;;
        "full")
            echo -e "${YELLOW}清理完整环境容器和镜像...${NC}"
            docker compose --profile full down --rmi all --volumes --remove-orphans
            echo -e "${GREEN}完整环境清理完成！${NC}"
            ;;
        "dev")
            echo -e "${YELLOW}清理开发环境容器和镜像...${NC}"
            docker compose --profile dev down --rmi all --volumes --remove-orphans
            echo -e "${GREEN}开发环境清理完成！${NC}"
            ;;
        "all")
            echo -e "${YELLOW}清理所有Biomni容器和镜像...${NC}"
            # 先停止所有容器
            docker compose --profile basic down
            docker compose --profile full down
            docker compose --profile dev down
            # 然后清理所有profile的容器和镜像
            docker compose --profile basic down --rmi all --volumes --remove-orphans
            docker compose --profile full down --rmi all --volumes --remove-orphans
            docker compose --profile dev down --rmi all --volumes --remove-orphans
            echo -e "${GREEN}所有环境清理完成！${NC}"
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, 或 all${NC}"
            exit 1
            ;;
    esac
}

# 查看容器日志
show_logs() {
    local profile=$1
    case $profile in
        "basic")
            docker compose --profile basic logs -f biomni-basic
            ;;
        "full")
            docker compose --profile full logs -f biomni-full
            ;;
        "dev")
            docker compose --profile dev logs -f biomni-dev
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
            docker compose --profile basic exec biomni-basic /bin/bash
            ;;
        "full")
            docker compose --profile full exec biomni-full /bin/bash
            ;;
        "dev")
            docker compose --profile dev exec biomni-dev /bin/bash
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
    
    if ! command -v docker compose &> /dev/null; then
        echo -e "${RED}错误: Docker Compose未安装！${NC}"
        echo "请先安装Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# 主函数
main() {
    check_docker
    
    # 检查是否有 -p 参数
    local progress_flag=""
    local args=("$@")
    
    # 处理 -p 参数
    for i in "${!args[@]}"; do
        if [[ "${args[$i]}" == "-p" ]]; then
            progress_flag="--progress=plain"
            # 移除 -p 参数
            unset args[$i]
            break
        fi
    done
    
    # 重新构建参数数组
    args=("${args[@]}")
    
    case ${args[0]} in
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
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定要构建的环境: basic, full, 或 dev${NC}"
                exit 1
            fi
            build_image "${args[1]}" "$progress_flag"
            ;;
        "stop")
            if [ -z "${args[1]}" ]; then
                stop_containers "all"
            else
                stop_containers "${args[1]}"
            fi
            ;;
        "clean")
            if [ -z "${args[1]}" ]; then
                clean_all "all"
            else
                clean_all "${args[1]}"
            fi
            ;;
        "logs")
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
                exit 1
            fi
            show_logs "${args[1]}"
            ;;
        "shell")
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定环境类型: basic, full, 或 dev${NC}"
                exit 1
            fi
            enter_shell "${args[1]}"
            ;;
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            echo -e "${RED}未知选项: ${args[0]}${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 
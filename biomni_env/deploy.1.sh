#!/bin/bash

# Biomni Docker 部署脚本 - 精简版
# 支持新旧版本容器管理（移除冗余的setup.1）

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
    echo "支持新旧版本容器管理"
    echo ""
    echo "用法: $0 [选项] [环境类型]"
    echo ""
    echo "环境类型:"
    echo "  basic       - 旧版基础环境（虚拟环境）"
    echo "  full        - 旧版完整环境（虚拟环境）"
    echo "  dev         - 旧版开发环境（虚拟环境）"
    echo "  basic.1     - 新版基础环境（conda环境，轻量）"
    echo "  full.1      - 新版完整环境（conda环境，已包含所有工具）"
    echo "  dev.1       - 新版开发环境（conda环境）"
    echo ""
    echo "选项:"
    echo "  build       - 仅构建镜像"
    echo "  stop        - 停止容器 (支持: basic, full, dev, basic.1, full.1, dev.1, all, all.1, all.all)"
    echo "  clean       - 清理容器和镜像 (支持: basic, full, dev, basic.1, full.1, dev.1, all, all.1, all.all)"
    echo "  logs        - 查看容器日志"
    echo "  shell       - 进入容器shell"
    echo "  status      - 查看容器状态"
    echo "  pull        - 拉取最新镜像"
    echo "  help        - 显示此帮助信息"
    echo ""
    echo "全局选项:"
    echo "  -p          - 构建时使用 --progress=plain 显示详细输出"
    echo ""
    echo "示例:"
    echo "  $0 basic.1      # 启动新版基础环境（轻量）"
    echo "  $0 full.1       # 启动新版完整环境（包含所有工具）"
    echo "  $0 build full.1 # 构建新版完整环境"
    echo "  $0 stop all.all # 停止所有环境"
    echo "  $0 status       # 查看所有容器状态"
    echo ""
    echo "注意：Dockerfile.1已集成完整环境，无需单独setup！"
}

# 创建必要的目录
create_directories() {
    echo -e "${YELLOW}创建必要的目录...${NC}"
    mkdir -p data notebooks results biomni_results
    echo -e "${GREEN}目录创建完成！${NC}"
}

# 构建镜像
build_image() {
    local profile=$1
    local progress_flag=$2
    echo -e "${YELLOW}构建 $profile 环境镜像...${NC}"
    
    case $profile in
        "basic"|"full"|"dev"|"basic.1"|"full.1"|"dev.1")
            docker compose --profile $profile build $progress_flag
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
            echo -e "${GREEN}旧版基础环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8888${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7860${NC}"
            ;;
        "full")
            docker compose --profile full up -d biomni-full
            echo -e "${GREEN}旧版完整环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8889${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7861${NC}"
            ;;
        "dev")
            docker compose --profile dev up -d biomni-dev
            echo -e "${GREEN}旧版开发环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:8890${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:7862${NC}"
            ;;
        "basic.1")
            docker compose --profile basic.1 up -d biomni-basic.1
            echo -e "${GREEN}新版基础环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:9998${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:9860${NC}"
            ;;
        "full.1")
            docker compose --profile full.1 up -d biomni-full.1
            echo -e "${GREEN}新版完整环境已启动！${NC}"
            echo -e "${BLUE}完整工具已集成，无需额外设置${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:9999${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:9861${NC}"
            ;;
        "dev.1")
            docker compose --profile dev.1 up -d biomni-dev.1
            echo -e "${GREEN}新版开发环境已启动！${NC}"
            echo -e "${BLUE}Jupyter Notebook: http://0.0.0.0:9990${NC}"
            echo -e "${BLUE}Gradio: http://0.0.0.0:9862${NC}"
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
        "basic"|"full"|"dev"|"basic.1"|"full.1"|"dev.1")
            echo -e "${YELLOW}停止 $profile 环境容器...${NC}"
            docker compose --profile $profile down
            echo -e "${GREEN}$profile 环境容器已停止！${NC}"
            ;;
        "all")
            echo -e "${YELLOW}停止所有旧版环境容器...${NC}"
            docker compose --profile basic down
            docker compose --profile full down
            docker compose --profile dev down
            echo -e "${GREEN}所有旧版环境容器已停止！${NC}"
            ;;
        "all.1")
            echo -e "${YELLOW}停止所有新版环境容器...${NC}"
            docker compose --profile basic.1 down
            docker compose --profile full.1 down
            docker compose --profile dev.1 down
            echo -e "${GREEN}所有新版环境容器已停止！${NC}"
            ;;
        "all.all")
            echo -e "${YELLOW}停止所有Biomni容器...${NC}"
            docker compose --profile basic down
            docker compose --profile full down
            docker compose --profile dev down
            docker compose --profile basic.1 down
            docker compose --profile full.1 down
            docker compose --profile dev.1 down
            echo -e "${GREEN}所有容器已停止！${NC}"
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, dev.1, all, all.1, 或 all.all${NC}"
            exit 1
            ;;
    esac
}

# 清理所有容器和镜像
clean_all() {
    local profile=$1
    
    case $profile in
        "basic"|"full"|"dev"|"basic.1"|"full.1"|"dev.1")
            echo -e "${YELLOW}清理 $profile 环境容器和镜像...${NC}"
            docker compose --profile $profile down --rmi local --volumes --remove-orphans
            echo -e "${GREEN}$profile 环境清理完成！${NC}"
            ;;
        "all")
            echo -e "${YELLOW}清理所有旧版环境容器和镜像...${NC}"
            docker compose --profile basic down --rmi local --volumes --remove-orphans
            docker compose --profile full down --rmi local --volumes --remove-orphans
            docker compose --profile dev down --rmi local --volumes --remove-orphans
            echo -e "${GREEN}所有旧版环境清理完成！${NC}"
            ;;
        "all.1")
            echo -e "${YELLOW}清理所有新版环境容器和镜像...${NC}"
            docker compose --profile basic.1 down --rmi local --volumes --remove-orphans
            docker compose --profile full.1 down --rmi local --volumes --remove-orphans
            docker compose --profile dev.1 down --rmi local --volumes --remove-orphans
            echo -e "${GREEN}所有新版环境清理完成！${NC}"
            ;;
        "all.all")
            echo -e "${YELLOW}清理所有Biomni容器和镜像...${NC}"
            docker compose --profile basic down
            docker compose --profile full down
            docker compose --profile dev down
            docker compose --profile basic.1 down
            docker compose --profile full.1 down
            docker compose --profile dev.1 down
            docker compose --profile basic down --rmi local --volumes --remove-orphans
            docker compose --profile full down --rmi local --volumes --remove-orphans
            docker compose --profile dev down --rmi local --volumes --remove-orphans
            docker compose --profile basic.1 down --rmi local --volumes --remove-orphans
            docker compose --profile full.1 down --rmi local --volumes --remove-orphans
            docker compose --profile dev.1 down --rmi local --volumes --remove-orphans
            echo -e "${GREEN}所有环境清理完成！${NC}"
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, dev.1, all, all.1, 或 all.all${NC}"
            exit 1
            ;;
    esac
}

# 查看容器日志
show_logs() {
    local profile=$1
    case $profile in
        "basic"|"full"|"dev"|"basic.1"|"full.1"|"dev.1")
            docker compose --profile $profile logs -f
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, 或 dev.1${NC}"
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
        "basic.1")
            docker compose --profile basic.1 exec biomni-basic.1 /bin/bash
            ;;
        "full.1")
            docker compose --profile full.1 exec biomni-full.1 /bin/bash
            ;;
        "dev.1")
            docker compose --profile dev.1 exec biomni-dev.1 /bin/bash
            ;;
        *)
            echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, 或 dev.1${NC}"
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
        "basic"|"full"|"dev"|"basic.1"|"full.1"|"dev.1")
            start_service "${args[0]}"
            ;;
        "build")
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定要构建的环境: basic, full, dev, basic.1, full.1, 或 dev.1${NC}"
                exit 1
            fi
            build_image "${args[1]}" "$progress_flag"
            ;;
        "stop")
            if [ -z "${args[1]}" ]; then
                stop_containers "all.all"
            else
                stop_containers "${args[1]}"
            fi
            ;;
        "clean")
            if [ -z "${args[1]}" ]; then
                clean_all "all.all"
            else
                clean_all "${args[1]}"
            fi
            ;;
        "logs")
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, 或 dev.1${NC}"
                exit 1
            fi
            show_logs "${args[1]}"
            ;;
        "shell")
            if [ -z "${args[1]}" ]; then
                echo -e "${RED}请指定环境类型: basic, full, dev, basic.1, full.1, 或 dev.1${NC}"
                exit 1
            fi
            enter_shell "${args[1]}"
            ;;
        "setup"|"setup.1")
            echo -e "${YELLOW}Dockerfile.1已包含完整环境，无需单独设置！${NC}"
            echo -e "${BLUE}直接使用：./deploy.1.sh full.1 即可${NC}"
            ;;
        "status")
            echo -e "${BLUE}Biomni容器状态:${NC}"
            echo -e "${YELLOW}旧版环境:${NC}"
            docker compose --profile basic ps -a
            docker compose --profile full ps -a
            docker compose --profile dev ps -a
            echo -e "${YELLOW}新版环境:${NC}"
            docker compose --profile basic.1 ps -a
            docker compose --profile full.1 ps -a
            docker compose --profile dev.1 ps -a
            ;;
        "pull")
            echo -e "${YELLOW}拉取最新镜像...${NC}"
            docker compose --profile basic pull
            docker compose --profile full pull
            docker compose --profile dev pull
            docker compose --profile basic.1 pull
            docker compose --profile full.1 pull
            docker compose --profile dev.1 pull
            echo -e "${GREEN}镜像拉取完成！${NC}"
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
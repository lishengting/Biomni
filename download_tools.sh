#!/bin/bash

# Biomni 命令行工具下载脚本
# 预先下载所有工具文件到downloads目录，避免在Docker构建时下载

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建downloads目录
DOWNLOAD_DIR="downloads"
mkdir -p "$DOWNLOAD_DIR"

echo -e "${YELLOW}=== Biomni 命令行工具下载脚本 ===${NC}"
echo -e "${BLUE}下载目录: $DOWNLOAD_DIR${NC}"

# 函数：下载文件
download_file() {
    local url=$1
    local filename=$2
    local description=$3
    
    echo -e "\n${YELLOW}下载 $description...${NC}"
    echo -e "URL: $url"
    echo -e "文件: $filename"
    
    if [ -f "$DOWNLOAD_DIR/$filename" ]; then
        echo -e "${GREEN}文件已存在，跳过下载${NC}"
        return 0
    fi
    
    if wget -O "$DOWNLOAD_DIR/$filename" "$url"; then
        echo -e "${GREEN}✓ $description 下载成功${NC}"
        return 0
    else
        echo -e "${RED}✗ $description 下载失败${NC}"
        return 1
    fi
}

# 下载PLINK2
download_file \
    "https://s3.amazonaws.com/plink2-assets/alpha6/plink2_linux_avx2_20250129.zip" \
    "plink2_linux_avx2_20250129.zip" \
    "PLINK2 (基因组关联分析工具)"

# 下载IQ-TREE
download_file \
    "https://github.com/iqtree/iqtree2/releases/download/v2.2.2.7/iqtree-2.2.2.7-Linux.tar.gz" \
    "iqtree-2.2.2.7-Linux.tar.gz" \
    "IQ-TREE (系统发育分析工具)"

# 下载GCTA
download_file \
    "https://yanglab.westlake.edu.cn/software/gcta/bin/gcta-1.94.4-linux-kernel-3-x86_64.zip" \
    "gcta-1.94.4-linux-kernel-3-x86_64.zip" \
    "GCTA (基因组复杂性状分析工具)"

# 下载FastTree源码
download_file \
    "https://morgannprice.github.io/fasttree/FastTree.c" \
    "FastTree.c" \
    "FastTree (快速系统发育树构建工具源码)"

# 下载MUSCLE
download_file \
    "https://github.com/rcedgar/muscle/releases/download/v5.3/muscle-linux-x86.v5.3" \
    "muscle-linux-x86.v5.3" \
    "MUSCLE (多序列比对工具)"

# 下载HOMER配置脚本
download_file \
    "http://homer.ucsd.edu/homer/configureHomer.pl" \
    "configureHomer.pl" \
    "HOMER (基序发现工具配置脚本)"

echo -e "\n${GREEN}=== 下载完成 ===${NC}"
echo -e "所有工具文件已下载到: ${YELLOW}$DOWNLOAD_DIR${NC}"
echo -e ""
echo -e "${BLUE}下载的文件列表:${NC}"
ls -la "$DOWNLOAD_DIR/"

echo -e "\n${YELLOW}现在可以在Dockerfile中使用这些文件了！${NC}"
echo -e "Dockerfile会自动从 $DOWNLOAD_DIR 目录复制这些文件。" 
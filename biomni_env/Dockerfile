# Biomni Environment Dockerfile
# 基于Ubuntu 22.04构建完整的生物信息学环境

FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/biomni_tools/bin:$PATH"
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 设置工作目录
WORKDIR /opt/biomni

# 安装基础工具和编译环境
RUN apt-get update && apt-get install -y \
    # 基础工具
    wget curl git vim nano htop \
    # 编译工具
    build-essential gcc g++ make cmake \
    # 其他基础依赖
    jq unzip zip bzip2 gzip \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Python 3.11（需要添加PPA）
RUN apt-get update && apt-get install -y \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils && \
    # 创建Python 3.11的符号链接
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    # 安装pip（PPA中没有python3.11-pip包，需要使用get-pip.py）
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
    # 清理缓存
    apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装R环境（R 4.4+）
RUN apt-get update && apt-get install -y \
    software-properties-common dirmngr apt-transport-https ca-certificates gnupg && \
    # 添加CRAN官方密钥和源
    wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | gpg --dearmor -o /usr/share/keyrings/r-project.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] https://cloud.r-project.org/bin/linux/ubuntu jammy-cran40/" | tee -a /etc/apt/sources.list.d/r-project.list && \
    apt-get update && \
    apt-get install -y r-base r-base-dev && \
    # 清理缓存
    apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装生物信息学依赖库
RUN apt-get update && apt-get install -y \
    # 压缩库
    libz-dev libbz2-dev liblzma-dev \
    # 网络和加密库
    libcurl4-openssl-dev libssl-dev \
    # XML和图像库
    libxml2-dev libpng-dev libjpeg-dev \
    libfreetype6-dev libtiff5-dev \
    # 图形库
    libcairo2-dev libpango1.0-dev \
    # 数学库
    libblas-dev liblapack-dev libgsl-dev \
    # 科学计算库
    libhdf5-dev libnetcdf-dev \
    # 序列分析工具
    samtools bcftools bedtools fastqc bowtie2 bwa \
    # NCBI工具
    ncbi-tools-bin ncbi-blast+ \
    # 序列比对工具  
    mafft \
    # 质量控制工具
    trimmomatic \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建biomni用户
RUN useradd -u 1005 -m -s /bin/bash biomni && \
    chown -R biomni:biomni /opt/biomni && \
    # 创建工具目录并设置权限（在切换到biomni用户之前）
    mkdir -p /opt/biomni_tools/bin && \
    chown -R biomni:biomni /opt/biomni_tools

# 切换到biomni用户
USER biomni

# 创建Python 3.11虚拟环境
RUN python3.11 -m venv /opt/biomni/venv
ENV PATH="/opt/biomni/venv/bin:$PATH"

# 复制pip配置文件
COPY --chown=biomni:biomni pip.conf /opt/biomni/

# 配置pip以支持更长的超时和重试
RUN . /opt/biomni/venv/bin/activate && \
    mkdir -p /opt/biomni/venv/pip && \
    cp /opt/biomni/pip.conf /opt/biomni/venv/pip/pip.conf && \
    # 同时复制到用户目录确保pip能找到配置
    mkdir -p /home/biomni/.pip && \
    cp /opt/biomni/pip.conf /home/biomni/.pip/pip.conf && \
    # 设置环境变量指向pip配置
    echo 'export PIP_CONFIG_FILE=/opt/biomni/venv/pip/pip.conf' >> /opt/biomni/venv/bin/activate && \
    # 激活虚拟环境并升级pip（使用配置后的pip）
    python --version && \
    pip config list && \
    pip install --upgrade pip setuptools wheel

# 复制环境文件
COPY --chown=biomni:biomni environment.yml /opt/biomni/
COPY --chown=biomni:biomni bio_env.yml /opt/biomni/
COPY --chown=biomni:biomni r_packages.yml /opt/biomni/

# 大包，单独安装
RUN . /opt/biomni/venv/bin/activate && \
    pip install scvi-tools

# 合并所有Python包安装为一个RUN命令，提升构建效率（原分散RUN命令已注释，见下方）
RUN . /opt/biomni/venv/bin/activate && \
    pip install \
        tqdm numpy==2.1 pandas matplotlib scipy statsmodels scikit-learn \
        gradio langchain langgraph==0.3.18 langchain_openai langchain_anthropic \
        langchain_community langchain-google-genai langchain_ollama openai \
        biopython scanpy scvelo biopandas \
        biotite opencv-python rdkit macs2 pymc3 cryosparc-tools lifelines \
        scikit-image googlesearch-python PyPDF2 gget faiss-cpu \
        cellxgene-census scikit-bio pymed arxiv scholarly umap-learn \
        scrublet harmony-pytorch pyliftover pytdc==0.4.0 pysam pyfaidx \
        pyranges pybedtools openmm pystan igraph pyscenic cooler \
        trackpy flowcytometrytools cellpose viennarna PyMassSpec \
        python-libsbml cobra reportlab hmmlearn msprime tskit \
        cyvcf2 pykalman community fanc \
        gseapy beautifulsoup4 lxml seaborn networkx requests pyyaml jupyter notebook ipykernel pytest

# 以下为原分散安装命令，已合并，注释掉以便追溯（合并原因：减少镜像层数、加速构建）
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install scvi-tools
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install tqdm numpy==2.1 pandas matplotlib scipy statsmodels scikit-learn 
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install gradio langchain langgraph==0.3.18 langchain_openai langchain_anthropic \
#                 langchain_community langchain-google-genai langchain_ollama openai
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install biopython scanpy scvelo biopandas
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install biotite opencv-python rdkit macs2 pymc3 cryosparc-tools lifelines
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install scikit-image googlesearch-python PyPDF2 gget faiss-cpu
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install cellxgene-census scikit-bio pymed arxiv scholarly umap-learn
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install scrublet harmony-pytorch pyliftover pytdc==0.4.0 pysam pyfaidx
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install pyranges pybedtools openmm pystan igraph pyscenic cooler
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install trackpy flowcytometrytools cellpose viennarna PyMassSpec
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install python-libsbml cobra reportlab hmmlearn msprime tskit
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install cyvcf2 pykalman community fanc
# RUN . /opt/biomni/venv/bin/activate && \
#     pip install gseapy beautifulsoup4 lxml seaborn networkx requests pyyaml jupyter notebook ipykernel pytest

# 开发模式安装biomni源码
# RUN /opt/biomni/venv/bin/pip install -e /opt/biomni

# 工具目录已在前面创建并设置权限

USER root

ENV MAKEFLAGS="-j16"
# 安装所有R包（合并多个RUN命令）
RUN Rscript -e "install.packages(c('ggplot2', 'dplyr', 'tidyr', 'readr', 'stringr', 'lme4'), repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "install.packages('Matrix', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "install.packages('Rcpp', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "install.packages(c('devtools', 'remotes'), repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "install.packages('harmony', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "if (!require('BiocManager', quietly = TRUE)) install.packages('BiocManager', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "BiocManager::install(version = BiocManager::version(), update = TRUE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('DESeq2', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('DADA2', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('xcms', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('FlowCore', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('edgeR', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('limma', update = FALSE, ask = FALSE)" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install('clusterProfiler', update = FALSE, ask = FALSE)" && \
    Rscript -e "install.packages('WGCNA', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "install.packages(c('dynamicTreeCut', 'fastcluster', 'matrixStats', 'Hmisc', 'foreach', 'doParallel'), repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "options(BioC_mirror='https://mirrors.westlake.edu.cn/bioconductor', repos='https://mirrors.ustc.edu.cn/CRAN/'); BiocManager::install(c('impute', 'preprocessCore', 'GO.db', 'AnnotationDbi'), update = FALSE, ask = FALSE)"

RUN Rscript -e "if (!require('devtools', quietly = TRUE)) install.packages('devtools', repos='https://mirrors.ustc.edu.cn/CRAN/')" && \
    Rscript -e "devtools::install_github('liulab-dfci/MAGeCKFlute')"

# 切换回biomni用户
USER biomni

# 复制CLI工具安装脚本
COPY --chown=biomni:biomni install_cli_tools.sh /opt/biomni/
COPY --chown=biomni:biomni cli_tools_config.json /opt/biomni/
COPY --chown=biomni:biomni install_r_packages.R /opt/biomni/

# 复制预下载的工具文件
COPY --chown=biomni:biomni downloads/ /opt/biomni/downloads/

# 安装命令行工具（使用预下载的文件）
RUN cd /opt/biomni && \
    chmod +x install_cli_tools.sh && \
    # 设置环境变量
    export BIOMNI_TOOLS_DIR="/opt/biomni_tools" && \
    export BIOMNI_AUTO_INSTALL=1 && \
    # 创建临时工作目录
    mkdir -p /opt/biomni/tmp_build && \
    # 安装PLINK2
    unzip /opt/biomni/downloads/plink2_linux_avx2_20250129.zip -d /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/plink2 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/plink2 && \
    # 安装IQ-TREE
    tar -xzf /opt/biomni/downloads/iqtree-2.2.2.7-Linux.tar.gz -C /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/iqtree-2.2.2.7-Linux/bin/iqtree2 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/iqtree2 && \
    # 安装GCTA
    unzip /opt/biomni/downloads/gcta-1.94.4-linux-kernel-3-x86_64.zip -d /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/gcta-1.94.4-linux-kernel-3-x86_64/gcta64 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/gcta64 && \
    # 安装FastTree
    gcc -O3 -finline-functions -funroll-loops -Wall -o /opt/biomni_tools/bin/FastTree /opt/biomni/downloads/FastTree.c -lm && \
    chmod +x /opt/biomni_tools/bin/FastTree && \
    # 安装MUSCLE
    cp /opt/biomni/downloads/muscle-linux-x86.v5.3 /opt/biomni_tools/bin/muscle && \
    chmod +x /opt/biomni_tools/bin/muscle && \
    # 安装HOMER
    mkdir -p /opt/biomni_tools/homer && \
    cp /opt/biomni/downloads/configureHomer.pl /opt/biomni_tools/homer/ && \
    chmod +x /opt/biomni_tools/homer/configureHomer.pl && \
    cd /opt/biomni_tools/homer && \
    ./configureHomer.pl -install && \
    # 检查HOMER安装是否成功
    if [ ! -d "/opt/biomni_tools/homer/bin" ] || [ -z "$(ls -A /opt/biomni_tools/homer/bin 2>/dev/null)" ]; then \
        echo "ERROR: HOMER installation failed! /opt/biomni_tools/homer/bin/ directory does not exist or is empty." && \
        echo "Please check the HOMER installation process." && \
        exit 1; \
    fi && \
    echo "HOMER installation successful. Found $(ls /opt/biomni_tools/homer/bin/ | wc -l) tools in bin directory." && \
    # 创建HOMER的符号链接到bin目录
    ln -sf /opt/biomni_tools/homer/bin/* /opt/biomni_tools/bin/ && \
    # 安装BWA（从GitHub克隆源码编译）
    git clone https://github.com/lh3/bwa.git /opt/biomni/tmp_build/bwa && \
    cd /opt/biomni/tmp_build/bwa && \
    make && \
    cp bwa /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/bwa && \
    # 清理临时文件
    rm -rf /opt/biomni/tmp_build

# 安装R包（切换到root用户安装，然后切换回biomni用户）

# 设置环境变量
ENV PATH="/opt/biomni/venv/bin:$PATH"
ENV HOMER="/opt/biomni_tools/homer"

# 创建自动激活虚拟环境的bash配置文件
RUN echo 'source /opt/biomni/venv/bin/activate' >> /home/biomni/.bashrc && \
    echo 'echo "🐍 Python virtual environment activated: $(python --version)"' >> /home/biomni/.bashrc && \
    echo 'echo "📁 Working directory: $(pwd)"' >> /home/biomni/.bashrc && \
    echo 'echo "🔧 Available tools: biomni_tools/bin is in PATH"' >> /home/biomni/.bashrc

# 暴露Jupyter和Gradio端口
EXPOSE 8888 7860

# 注释掉ENTRYPOINT，让docker-compose.yml的command完全控制
# ENTRYPOINT ["/bin/bash", "/opt/biomni/scripts/start.sh"]

# 默认命令
CMD ["/bin/bash"] 
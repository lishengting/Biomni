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

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    wget curl git vim nano htop \
    # 编译工具
    build-essential gcc g++ make cmake \
    # Python相关
    python3 python3-pip python3-dev python3-venv \
    # R相关
    r-base r-base-dev \
    # 生物信息学依赖
    libz-dev libbz2-dev liblzma-dev libcurl4-openssl-dev \
    libssl-dev libxml2-dev libpng-dev libjpeg-dev \
    libfreetype6-dev libtiff5-dev libcairo2-dev \
    libpango1.0-dev libblas-dev liblapack-dev \
    libgsl-dev libhdf5-dev libnetcdf-dev \
    # 生物信息学命令行工具（对应bio_env.yml中的conda包）
    samtools bcftools bedtools fastqc bowtie2 bwa \
    # 序列分析工具
    blast2 ncbi-blast+ \
    # 序列比对工具  
    mafft \
    # 质量控制工具
    trimmomatic \
    # 其他依赖
    jq unzip zip bzip2 gzip \
    gosu \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建biomni用户
RUN useradd -u 1005 -m -s /bin/bash biomni && \
    chown -R biomni:biomni /opt/biomni

# 创建工具目录并设置权限（在切换到biomni用户之前）
RUN mkdir -p /opt/biomni_tools/bin && \
    chown -R biomni:biomni /opt/biomni_tools

# 切换到biomni用户
USER biomni

# 创建Python虚拟环境
RUN python3 -m venv /opt/biomni/venv
ENV PATH="/opt/biomni/venv/bin:$PATH"

# 激活虚拟环境并升级pip
RUN . /opt/biomni/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel

# 复制环境文件
COPY --chown=biomni:biomni environment.yml /opt/biomni/
COPY --chown=biomni:biomni bio_env.yml /opt/biomni/
COPY --chown=biomni:biomni r_packages.yml /opt/biomni/

# 安装Python包（使用pip而不是conda）
RUN . /opt/biomni/venv/bin/activate && \
    # 安装基础科学计算包
    pip install numpy==2.1 pandas matplotlib scipy statsmodels scikit-learn && \
    # 安装AI/ML相关包
    pip install gradio langchain langgraph==0.3.18 langchain_openai langchain_anthropic \
                langchain_community langchain-google-genai langchain_ollama openai && \
    # 安装生物信息学包
    pip install biopython scanpy scvelo scvi-tools biopandas biotite && \
    pip install opencv-python rdkit macs2 pymc3 cryosparc-tools lifelines && \
    pip install scikit-image googlesearch-python PyPDF2 gget faiss-cpu && \
    pip install cellxgene-census scikit-bio pymed arxiv scholarly umap-learn && \
    pip install scrublet harmony-pytorch pyliftover pytdc==0.4.0 pysam pyfaidx && \
    pip install pyranges pybedtools openmm pystan igraph pyscenic cooler && \
    pip install trackpy flowcytometrytools cellpose viennarna PyMassSpec && \
    pip install python-libsbml cobra reportlab hmmlearn msprime tskit && \
    pip install cyvcf2 pykalman community fanc && \
    # 安装其他工具包
    pip install beautifulsoup4 lxml tqdm seaborn networkx requests pyyaml && \
    pip install jupyter notebook ipykernel pytest

# 开发模式安装biomni源码
# RUN /opt/biomni/venv/bin/pip install -e /opt/biomni

# 工具目录已在前面创建并设置权限

# 复制CLI工具安装脚本
COPY --chown=biomni:biomni install_cli_tools.sh /opt/biomni/
COPY --chown=biomni:biomni cli_tools_config.json /opt/biomni/
COPY --chown=biomni:biomni install_r_packages.R /opt/biomni/

# 安装命令行工具
RUN cd /opt/biomni && \
    chmod +x install_cli_tools.sh && \
    # 设置环境变量
    export BIOMNI_TOOLS_DIR="/opt/biomni_tools" && \
    export BIOMNI_AUTO_INSTALL=1 && \
    # 创建临时工作目录
    mkdir -p /opt/biomni/tmp_build && \
    # 安装PLINK2
    wget -O /opt/biomni/tmp_build/plink2.zip "https://s3.amazonaws.com/plink2-assets/alpha6/plink2_linux_avx2_20250129.zip" && \
    unzip /opt/biomni/tmp_build/plink2.zip -d /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/plink2 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/plink2 && \
    # 安装IQ-TREE
    wget -O /opt/biomni/tmp_build/iqtree.tar.gz "https://github.com/iqtree/iqtree2/releases/download/v2.2.2.7/iqtree-2.2.2.7-Linux.tar.gz" && \
    tar -xzf /opt/biomni/tmp_build/iqtree.tar.gz -C /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/iqtree-2.2.2.7-Linux/bin/iqtree2 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/iqtree2 && \
    # 安装GCTA
    wget -O /opt/biomni/tmp_build/gcta.zip "https://yanglab.westlake.edu.cn/software/gcta/bin/gcta-1.94.4-linux-kernel-3-x86_64.zip" && \
    unzip /opt/biomni/tmp_build/gcta.zip -d /opt/biomni/tmp_build/ && \
    cp /opt/biomni/tmp_build/gcta64 /opt/biomni_tools/bin/ && \
    chmod +x /opt/biomni_tools/bin/gcta64 && \
    # 安装FastTree
    wget -O /opt/biomni/tmp_build/FastTree.c "https://morgannprice.github.io/fasttree/FastTree.c" && \
    gcc -O3 -finline-functions -funroll-loops -Wall -o /opt/biomni_tools/bin/FastTree /opt/biomni/tmp_build/FastTree.c -lm && \
    chmod +x /opt/biomni_tools/bin/FastTree && \
    # 安装MUSCLE
    wget -O /opt/biomni_tools/bin/muscle "https://github.com/rcedgar/muscle/releases/download/v5.3/muscle-linux-x86.v5.3" && \
    chmod +x /opt/biomni_tools/bin/muscle && \
    # 安装HOMER
    wget -O /opt/biomni_tools/bin/configureHomer.pl "http://homer.ucsd.edu/homer/configureHomer.pl" && \
    chmod +x /opt/biomni_tools/bin/configureHomer.pl && \
    mkdir -p /opt/biomni_tools/homer && \
    /opt/biomni_tools/bin/configureHomer.pl -install -local /opt/biomni_tools/homer -b && \
    # 创建HOMER的符号链接
    ln -sf /opt/biomni_tools/homer/bin/* /opt/biomni_tools/bin/ && \
    # 清理临时文件
    rm -rf /opt/biomni/tmp_build

# 安装R包
RUN Rscript -e "install.packages(c('ggplot2', 'dplyr', 'tidyr', 'readr', 'stringr', 'Matrix', 'Rcpp', 'devtools', 'remotes', 'harmony'), repos='https://cran.rstudio.com/')" && \
    Rscript -e "if (!require('BiocManager', quietly = TRUE)) install.packages('BiocManager', repos='https://cran.rstudio.com/')" && \
    Rscript -e "BiocManager::install(c('DESeq2', 'DADA2', 'xcms', 'FlowCore', 'edgeR', 'limma', 'clusterProfiler'), update = FALSE, ask = FALSE)" && \
    Rscript -e "install.packages('WGCNA', repos='https://cran.rstudio.com/')"

# 创建启动脚本
# RUN echo '#!/bin/bash' > /opt/biomni/start.sh && \
#     echo 'export PATH="/opt/biomni_tools/bin:$PATH"' >> /opt/biomni/start.sh && \
#     echo 'export PATH="/opt/biomni/venv/bin:$PATH"' >> /opt/biomni/start.sh && \
#     echo 'export HOMER="/opt/biomni_tools/homer"' >> /opt/biomni/start.sh && \
#     echo 'echo "Biomni environment activated!"' >> /opt/biomni/start.sh && \
#     echo 'echo "Available tools:"' >> /opt/biomni/start.sh && \
#     echo 'ls -la /opt/biomni_tools/bin/' >> /opt/biomni/start.sh && \
#     echo 'echo "Python packages:"' >> /opt/biomni/start.sh && \
#     echo 'pip list' >> /opt/biomni/start.sh && \
#     echo 'echo "Switching to biomni user..."' >> /opt/biomni/start.sh && \
#     echo 'exec gosu biomni "$@"' >> /opt/biomni/start.sh && \
#     chmod +x /opt/biomni/start.sh

# 拷贝通用脚本
# COPY scripts/start.sh /opt/biomni/start.sh
# COPY scripts/gradio_app.py /opt/biomni/gradio_app.py
# RUN chmod +x /opt/biomni/start.sh

# 设置环境变量
ENV PATH="/opt/biomni_tools/bin:/opt/biomni/venv/bin:$PATH"
ENV HOMER="/opt/biomni_tools/homer"

# 暴露Jupyter和Gradio端口
EXPOSE 8888 7860

# 设置入口点（脚本通过docker-compose.yml挂载）
ENTRYPOINT ["/opt/biomni/start.sh"]

# 默认命令
CMD ["/bin/bash"] 
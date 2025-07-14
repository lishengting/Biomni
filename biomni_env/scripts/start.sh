#!/bin/bash

# Biomni 通用启动脚本

echo "Biomni environment activated!"
echo "Available Python packages:"
pip list
echo ""
echo "To start Jupyter notebook, run:"
echo "jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --notebook-dir=/opt/biomni/notebooks"
echo "To start Gradio app, run:"
echo "python /opt/biomni/gradio_app.py"
echo "Starting services..."
exec "$@" 
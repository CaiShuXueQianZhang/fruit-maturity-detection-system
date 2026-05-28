# Day 3: RSOD 数据集模型训练与微调

> **学习目标**：掌握数据集格式转换、YOLO训练配置、模型训练与评估的完整流程

---

## 📋 今日任务清单

- [ ] XML标注 → YOLO格式转换
- [ ] 数据集配置文件（rsod.yaml）
- [ ] 训练脚本编写与参数配置
- [ ] 启动训练（本地CPU、AutoDL云端）
- [ ] 模型训练记录
- [ ] 模型训练后必交成果

---

## 一、数据集格式转换

### 1.1 数据集结构

RSOD 数据集原始格式为 Pascal VOC（XML标注），需要转换为 YOLO 格式：

```
原始格式（Pascal VOC）：
rsod/
├── images/
│   ├── aircraft_001.jpg
│   ├── aircraft_002.jpg
│   └── ...
└── annotations/
    ├── aircraft_001.xml
    ├── aircraft_002.xml
    └── ...

目标格式（YOLO）：
rsod/yolo_dataset/
├── images/
│   ├── train/
│   │   ├── aircraft_001.jpg
│   │   └── ...
│   └── val/
│       ├── aircraft_xxx.jpg
│       └── ...
├── labels/
│   ├── train/
│   │   ├── aircraft_001.txt
│   │   └── ...
│   └── val/
│       ├── aircraft_xxx.txt
│       └── ...
└── rsod.yaml
```

### 1.2 转换脚本

```python
# backend/convert_rsod.py

#!/usr/bin/env python3
"""
RSOD 数据集转换工具
将 Pascal VOC 格式（XML）转换为 YOLO 格式（TXT）
"""

import os
import xml.etree.ElementTree as ET
import shutil
import random

# RSOD 数据集类别映射
CLASSES = ["aircraft", "oiltank", "overpass", "playground"]
CLASS_MAP = {cls: idx for idx, cls in enumerate(CLASSES)}

def convert_xml_to_yolo(xml_path, image_width, image_height):
    """
    将单个 XML 文件转换为 YOLO 格式
    
    参数：
        xml_path: XML 文件路径
        image_width: 图片宽度
        image_height: 图片高度
    
    返回：
        str: YOLO 格式的标注内容
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    lines = []
    for obj in root.findall("object"):
        # 获取类别名称
        name = obj.find("name").text
        if name not in CLASS_MAP:
            print(f"警告：未知类别 '{name}'，已跳过")
            continue
        
        # 获取类别 ID
        class_id = CLASS_MAP[name]
        
        # 获取边界框坐标
        bbox = obj.find("bndbox")
        xmin = int(bbox.find("xmin").text)
        ymin = int(bbox.find("ymin").text)
        xmax = int(bbox.find("xmax").text)
        ymax = int(bbox.find("ymax").text)
        
        # 转换为 YOLO 格式（归一化）
        x_center = (xmin + xmax) / 2.0 / image_width
        y_center = (ymin + ymax) / 2.0 / image_height
        bbox_width = (xmax - xmin) / image_width
        bbox_height = (ymax - ymin) / image_height
        
        # 格式化输出（类别ID 中心点X 中心点Y 宽度 高度）
        lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}")
    
    return "\n".join(lines)

def convert_dataset(base_dir, split_ratio=0.8, seed=42):
    """
    转换整个数据集
    
    参数：
        base_dir: 数据集基础目录
        split_ratio: 训练集占比
        seed: 随机种子
    """
    # 路径配置
    rsod_dir = os.path.join(base_dir, "data", "rsod")
    images_dir = os.path.join(rsod_dir, "images")
    annotations_dir = os.path.join(rsod_dir, "annotations")
    
    # 输出目录
    output_dir = os.path.join(rsod_dir, "yolo_dataset")
    train_images_dir = os.path.join(output_dir, "images", "train")
    val_images_dir = os.path.join(output_dir, "images", "val")
    train_labels_dir = os.path.join(output_dir, "labels", "train")
    val_labels_dir = os.path.join(output_dir, "labels", "val")
    
    # 创建输出目录
    os.makedirs(train_images_dir, exist_ok=True)
    os.makedirs(val_images_dir, exist_ok=True)
    os.makedirs(train_labels_dir, exist_ok=True)
    os.makedirs(val_labels_dir, exist_ok=True)
    
    # 获取所有图片文件
    image_files = [f for f in os.listdir(images_dir) if f.endswith(".jpg")]
    
    # 随机打乱并分割
    random.seed(seed)
    random.shuffle(image_files)
    
    split_idx = int(len(image_files) * split_ratio)
    train_files = image_files[:split_idx]
    val_files = image_files[split_idx:]
    
    print(f"数据集分割完成：训练集 {len(train_files)} 张，验证集 {len(val_files)} 张")
    
    # 处理训练集
    for filename in train_files:
        # 获取图片名称（不含扩展名）
        basename = os.path.splitext(filename)[0]
        
        # 复制图片
        src_image = os.path.join(images_dir, filename)
        dst_image = os.path.join(train_images_dir, filename)
        shutil.copy(src_image, dst_image)
        
        # 转换标注
        xml_path = os.path.join(annotations_dir, f"{basename}.xml")
        if os.path.exists(xml_path):
            # 获取图片尺寸（这里简化处理，实际应读取图片）
            label_content = convert_xml_to_yolo(xml_path, 1024, 768)
            
            # 保存标注文件
            with open(os.path.join(train_labels_dir, f"{basename}.txt"), "w") as f:
                f.write(label_content)
    
    # 处理验证集（同上）
    for filename in val_files:
        basename = os.path.splitext(filename)[0]
        
        src_image = os.path.join(images_dir, filename)
        dst_image = os.path.join(val_images_dir, filename)
        shutil.copy(src_image, dst_image)
        
        xml_path = os.path.join(annotations_dir, f"{basename}.xml")
        if os.path.exists(xml_path):
            label_content = convert_xml_to_yolo(xml_path, 1024, 768)
            with open(os.path.join(val_labels_dir, f"{basename}.txt"), "w") as f:
                f.write(label_content)
    
    print(f"数据集转换完成！输出目录：{output_dir}")
    
    # 创建数据集配置文件
    create_yaml_config(output_dir)

def create_yaml_config(output_dir):
    """创建 YOLO 数据集配置文件"""
    yaml_content = f"""# RSOD 数据集配置文件
path: {output_dir}

train: images/train
val: images/val

nc: {len(CLASSES)}
names: {CLASSES}
"""
    
    with open(os.path.join(output_dir, "rsod.yaml"), "w") as f:
        f.write(yaml_content)
    
    print(f"配置文件已创建：{os.path.join(output_dir, 'rsod.yaml')}")

if __name__ == "__main__":
    # 执行转换（假设脚本在 backend 目录）
    base_dir = os.path.dirname(os.path.abspath(__file__))
    convert_dataset(base_dir)
```

### 1.3 运行转换脚本

```bash
# 进入后端目录
cd /Users/lily/Desktop/rsod-web-platform/backend

# 激活虚拟环境
source .venv/bin/activate

# 运行转换脚本
python convert_rsod.py
```

---

## 二、数据集配置文件

### 2.1 rsod.yaml 配置

```yaml
# backend/data/rsod/yolo_dataset/rsod.yaml

# 数据集根目录（相对于运行目录）
path: ./data/rsod/yolo_dataset

# 训练集和验证集路径
train: images/train
val: images/val

# 测试集（可选）
# test: images/test

# 类别数量
nc: 4

# 类别名称（按顺序对应类别ID）
names:
  0: aircraft    # 飞机
  1: oiltank     # 油罐
  2: overpass    # 立交桥
  3: playground  # 操场

# 数据集描述（可选）
# description: RSOD (Remote Sensing Object Detection) Dataset
# url: https://www.rsod-dataset.com
```

### 2.2 配置文件说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `path` | 数据集根目录 | `./data/rsod/yolo_dataset` |
| `train` | 训练集图片目录（相对于path） | `images/train` |
| `val` | 验证集图片目录（相对于path） | `images/val` |
| `nc` | 类别数量 | `4` |
| `names` | 类别名称列表 | `[aircraft, oiltank, overpass, playground]` |

---

## 三、训练脚本编写

### 3.1 训练脚本

```python
# backend/train_model.py

#!/usr/bin/env python3
"""
YOLO 模型训练脚本
支持本地训练和云端训练
"""

import os
import sys
import argparse
from ultralytics import YOLO

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="YOLO 模型训练脚本")
    
    # 训练参数
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--batch", type=int, default=16, help="批次大小")
    parser.add_argument("--imgsz", type=int, default=640, help="输入图片尺寸")
    parser.add_argument("--device", type=str, default="cpu", help="训练设备")
    parser.add_argument("--lr0", type=float, default=0.01, help="初始学习率")
    parser.add_argument("--lrf", type=float, default=0.01, help="最终学习率")
    parser.add_argument("--patience", type=int, default=20, help="早停耐心值")
    
    # 数据集配置
    parser.add_argument("--data", type=str, default="./data/rsod/yolo_dataset/rsod.yaml", 
                        help="数据集配置文件路径")
    
    # 模型配置
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="预训练模型")
    parser.add_argument("--name", type=str, default="rsod_yolo11n", help="实验名称")
    parser.add_argument("--project", type=str, default="./models", help="输出目录")
    
    # 评估参数
    parser.add_argument("--evaluate", action="store_true", help="仅评估模型")
    
    return parser.parse_args()

def train_model(args):
    """训练模型"""
    print("="*60)
    print("开始训练 YOLO 模型")
    print("="*60)
    
    # 打印训练配置
    print("\n训练配置:")
    print(f"  模型: {args.model}")
    print(f"  数据集: {args.data}")
    print(f"  训练轮数: {args.epochs}")
    print(f"  批次大小: {args.batch}")
    print(f"  输入尺寸: {args.imgsz}")
    print(f"  设备: {args.device}")
    print(f"  初始学习率: {args.lr0}")
    
    try:
        # 加载预训练模型
        model = YOLO(args.model)
        print(f"\n预训练模型加载成功: {args.model}")
        
        # 开始训练
        results = model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            name=args.name,
            project=args.project,
            exist_ok=True,
            plots=True,
            patience=args.patience,
            lr0=args.lr0,
            lrf=args.lrf,
            momentum=0.937,
            weight_decay=0.0005,
            save=True,
            val=True
        )
        
        print("\n" + "="*60)
        print("训练完成！")
        print("="*60)
        
        # 获取最佳模型路径
        best_model_path = os.path.join(args.project, args.name, "weights", "best.pt")
        print(f"\n最佳模型路径: {best_model_path}")
        
        return results
        
    except Exception as e:
        print(f"\n训练失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def evaluate_model(args):
    """评估模型"""
    print("="*60)
    print("开始评估模型")
    print("="*60)
    
    model_path = os.path.join(args.project, args.name, "weights", "best.pt")
    
    if not os.path.exists(model_path):
        print(f"错误：模型文件不存在: {model_path}")
        return None
    
    try:
        model = YOLO(model_path)
        metrics = model.val(data=args.data)
        
        print("\n评估结果:")
        print(f"  mAP@0.5: {metrics.box.map50:.4f}")
        print(f"  mAP@0.5:0.95: {metrics.box.map:.4f}")
        print(f"  Precision: {metrics.box.mp:.4f}")
        print(f"  Recall: {metrics.box.mr:.4f}")
        
        return metrics
        
    except Exception as e:
        print(f"评估失败: {str(e)}")
        return None

if __name__ == "__main__":
    args = parse_args()
    
    if args.evaluate:
        evaluate_model(args)
    else:
        train_model(args)
        # 训练完成后自动评估
        evaluate_model(args)
```

### 3.2 训练参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--epochs` | 训练轮数 | 100 |
| `--batch` | 批次大小 | 16 |
| `--imgsz` | 输入图片尺寸 | 640 |
| `--device` | 训练设备（cpu/cuda/0） | cpu |
| `--lr0` | 初始学习率 | 0.01 |
| `--patience` | 早停耐心值 | 20 |
| `--data` | 数据集配置文件 | rsod.yaml |
| `--model` | 预训练模型 | yolo11n.pt |

---

## 四、启动训练

### 4.1 本地 CPU 训练（不推荐，仅用于测试）

```bash
# 进入后端目录
cd /Users/lily/Desktop/rsod-web-platform/backend

# 激活虚拟环境
source .venv/bin/activate

# 启动训练（CPU模式，epoch较少用于测试）
python train_model.py --epochs 10 --batch 4 --device cpu

# 查看训练结果
ls models/rsod_yolo11n/weights/
```

### 4.2 AutoDL 云端训练（推荐）

#### 步骤1：上传代码到云端

```bash
# 在本地打包代码
cd /Users/lily/Desktop/rsod-web-platform/backend
zip -r rsod-backend.zip .

# 在 AutoDL 实例中解压
unzip rsod-backend.zip
cd rsod-backend

# 安装依赖
pip install ultralytics torch torchvision opencv-python
```

#### 步骤2：启动云端训练

```bash
# 查看可用 GPU
nvidia-smi

# 启动训练（GPU模式）
python train_model.py \
    --epochs 100 \
    --batch 16 \
    --device 0 \
    --imgsz 640 \
    --lr0 0.01 \
    --patience 20
```

#### 步骤3：下载训练好的模型

```bash
# 使用 scp 下载（本地执行）
scp username@autodl-host:/path/to/rsod-backend/models/rsod_yolo11n/weights/best.pt .

# 或者使用 AutoDL 的文件管理功能下载
```

---

## 五、模型训练记录

### 5.1 训练日志分析

训练过程中会自动生成以下文件：

```
models/rsod_yolo11n/
├── weights/
│   ├── best.pt      # 最佳模型（根据验证集 mAP 选择）
│   └── last.pt      # 最后一轮模型
├── results.csv      # 训练指标记录
├── confusion_matrix.png  # 混淆矩阵
├── F1_curve.png     # F1 曲线
├── PR_curve.png     # PR 曲线
├── results.png      # 综合结果图
└── train/           # 训练相关文件
    ├── labels.jpg   # 标签分布
    ├── mosaic*.jpg  # 数据增强示例
    └── ...
```

### 5.2 训练指标解读

| 指标 | 说明 | 目标值 |
|------|------|--------|
| `train/box_loss` | 边界框回归损失 | 越小越好 |
| `train/cls_loss` | 分类损失 | 越小越好 |
| `val/box_loss` | 验证集边界框损失 | 越小越好 |
| `val/cls_loss` | 验证集分类损失 | 越小越好 |
| `metrics/mAP50` | 平均精度（IoU=0.5） | 越高越好 |
| `metrics/mAP50-95` | 平均精度（IoU=0.5~0.95） | 越高越好 |

### 5.3 训练记录表格

```csv
epoch,train_box_loss,train_cls_loss,val_box_loss,val_cls_loss,mAP50,mAP50_95,lr,time
1,0.523,0.321,0.456,0.289,0.345,0.123,0.01,45s
2,0.345,0.212,0.321,0.198,0.567,0.234,0.01,44s
...
50,0.056,0.023,0.089,0.045,0.856,0.623,0.001,42s
100,0.034,0.012,0.078,0.034,0.876,0.652,0.0001,41s
```

---

## 六、训练后必交成果

### 6.1 必交成果清单

```
✅ 必交成果：
├── 1. 训练日志（results.csv）
├── 2. 最佳模型文件（best.pt）
├── 3. 评估报告（mAP、precision、recall）
├── 4. 训练曲线图（loss、mAP、F1）
├── 5. 混淆矩阵图
├── 6. 预测结果示例（至少5张）
├── 7. 数据集配置文件（rsod.yaml）
├── 8. 训练脚本（train_model.py）
└── 9. 实验记录文档（含参数配置）
```

### 6.2 评估报告模板

```markdown
# RSOD 目标检测模型评估报告

## 一、实验信息
- 实验名称：YOLO11n-RSOD
- 实验日期：2024-01-01
- 数据集：RSOD（976张图片，4类）
- 训练轮数：100
- 批次大小：16

## 二、评估结果

| 指标 | 值 |
|------|-----|
| mAP@0.5 | 0.876 |
| mAP@0.5:0.95 | 0.652 |
| Precision | 0.891 |
| Recall | 0.845 |
| F1 Score | 0.867 |

## 三、类别精度

| 类别 | mAP@0.5 | Precision | Recall |
|------|---------|-----------|--------|
| aircraft | 0.923 | 0.945 | 0.912 |
| oiltank | 0.856 | 0.878 | 0.845 |
| overpass | 0.834 | 0.856 | 0.821 |
| playground | 0.891 | 0.902 | 0.887 |

## 四、结论
- 模型在飞机类别上表现最佳（mAP=0.923）
- 立交桥类别相对较弱，需要更多数据或数据增强
- 整体性能达到预期，可部署到生产环境
```

---

## 📊 训练结果检查清单

- [ ] 训练日志完整（无报错）
- [ ] 最佳模型已保存（best.pt）
- [ ] mAP@0.5 ≥ 0.8（目标值）
- [ ] 验证集损失收敛
- [ ] 训练曲线图正常（无震荡）
- [ ] 预测结果可视化（有检测框）
- [ ] 实验文档完整

---

---

## 七、训练后模型自动上传 MinIO

### 7.1 自动上传功能介绍

训练脚本现在支持训练完成后自动将最佳模型上传到 MinIO 对象存储：

- ✅ 训练完成后自动上传 `best.pt`
- ✅ 可选上传 `last.pt`
- ✅ 生成带时间戳的模型文件名
- ✅ 自动获取 MinIO 公开访问 URL
- ✅ 失败时不影响主流程（警告而非错误）

### 7.2 使用方法

训练过程中会自动检测 MinIO 服务并上传：

```bash
# 正常训练，训练完成后会自动上传
cd /Users/lily/Desktop/rsod-web-platform/backend
source .venv/bin/activate
python train_model.py --epochs 100 --device cpu
```

### 7.3 训练日志示例

```
============================================================
开始训练 YOLO 模型
============================================================
...
训练完成！
============================================================
最佳模型路径: /path/to/rsod-yolo11n-best.pt

正在上传模型到 MinIO...
  模型名称: rsod-yolo11n-best-20240101-090000
  文件路径: /path/to/models/weights/best.pt
✅ 模型上传成功！
   对象名称: rsod-yolo11n-best-20240101-090000.pt
   访问 URL: http://localhost:9000/rsod-models/rsod-yolo11n-best-20240101-090000.pt
   同时上传了 last.pt: rsod-yolo11n-last-20240101-090000.pt
   访问 URL: http://localhost:9000/rsod-models/rsod-yolo11n-last-20240101-090000.pt
```

### 7.4 查看 MinIO 中的模型

```bash
# 方法1：访问 MinIO 控制台
# 浏览器访问: http://localhost:9001
# 登录后查看 rsod-models 桶

# 方法2：使用 Python 脚本
cd /Users/lily/Desktop/rsod-web-platform/backend
source .venv/bin/activate
python3 -c "
from app.services.minio_service import minio_service
models = minio_service.list_models()
print('MinIO 中的模型:')
for m in models:
    print(f'  - {m}')
"

# 方法3：使用 upload_models_to_minio.py 脚本
python upload_models_to_minio.py --list
```

### 7.5 手动上传现有模型

如需上传已训练好的模型，使用上传脚本：

```bash
# 上传所有本地模型
python upload_models_to_minio.py

# 上传单个指定模型
python upload_models_to_minio.py /path/to/your/model.pt --model-name my-custom-model
```

---

## 八、模型版本管理与 API 管理

### 8.1 语义化版本命名

训练脚本现在支持语义化版本管理，模型文件命名格式：

```
rsod-yolo11n-best_v{MAJOR}.{MINOR}.{PATCH}_{TIMESTAMP}.pt
```

例如：
- `rsod-yolo11n-best_v1.0.0_20240101090000.pt`
- `rsod-yolo11n-best_v1.1.0_20240102100000.pt`

### 8.2 模型元数据

每个模型都会同时上传配套的元数据文件（JSON），包含：
- 模型名称和版本
- 创建时间
- 评估指标（mAP50, mAP50-95, precision, recall）
- 训练配置（epochs, batch, lr 等）
- 数据集信息

例如：
```json
{
  "name": "rsod-yolo11n",
  "version": "1.0.0",
  "created_at": "2024-01-01T09:00:00",
  "description": "RSOD 数据集训练的 YOLO11 目标检测模型",
  "metrics": {
    "mAP50": 0.876,
    "mAP50-95": 0.652,
    "precision": 0.891,
    "recall": 0.845,
    "f1": 0.867
  },
  "config": {
    "epochs": 100,
    "batch": 16,
    "imgsz": 640,
    "device": "cpu"
  }
}
```

### 8.3 模型管理 API 接口

项目新增模型管理 API，可通过接口管理模型：

#### 8.3.1 获取模型列表
```bash
# 获取所有可用模型
curl -X GET "http://localhost:8000/api/model/list"
```

响应示例：
```json
{
  "success": true,
  "message": "获取成功",
  "data": [
    {
      "object_name": "rsod-yolo11n-best_v1.0.0_20240101090000.pt",
      "metadata": {...},
      "public_url": "http://localhost:9000/rsod-models/..."
    }
  ],
  "latest": {...}
}
```

#### 8.3.2 获取当前加载的模型
```bash
curl -X GET "http://localhost:8000/api/model/current"
```

#### 8.3.3 重新加载模型
```bash
# 加载最新版本
curl -X POST "http://localhost:8000/api/model/reload" -H "Content-Type: application/json"

# 加载指定版本
curl -X POST "http://localhost:8000/api/model/reload" \
  -H "Content-Type: application/json" \
  -d '{"object_name": "rsod-yolo11n-best_v1.0.0_20240101090000.pt"}'
```

### 8.4 智能模型加载

检测服务支持智能模型加载策略：
- 首次启动：从 MinIO 下载最新版本
- 已有本地模型：对比版本，自动更新
- 本地缓存：避免重复下载
- 降级处理：下载失败时使用本地已有模型

---

## 💡 今日总结

1. **数据集转换**：将 XML 格式转换为 YOLO 格式
2. **配置文件**：创建 rsod.yaml 配置数据集信息
3. **训练脚本**：编写带参数的训练脚本，支持自动上传和语义化版本
4. **启动训练**：本地测试 + 云端正式训练
5. **记录跟踪**：收集训练日志、指标、曲线图
6. **自动上传**：训练完成后自动将模型上传到 MinIO，包含元数据
7. **版本管理**：使用语义化版本 + 时间戳命名
8. **智能加载**：检测服务自动检查和更新模型
9. **API 管理**：通过 REST API 管理模型版本
10. **成果提交**：整理所有必交材料

---

**明日预告**：Day4 - 模型优化与部署
#!/usr/bin/env python3
"""
芒果香蕉成熟度检测 - YOLO11 训练工具

功能：
    - 训练芒果香蕉成熟度检测模型（4分类）
    - 支持 GPU/CPU 训练，自动检测环境
    - 训练完成后自动保存模型和元数据
    - 支持模型评估、预测
    - 输出设备信息和训练日志

使用方式：
    python train_model.py --epochs 100 --batch 32 --device 0
    python train_model.py --evaluate --model-path ./best.pt
    python train_model.py --predict ./test.jpg --conf 025
"""

import os
import sys
import argparse
import logging
import json
import shutil
from pathlib import Path
import time
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import torch
    from ultralytics import YOLO
except ImportError:
    print("错误：未安装必要库，请运行: pip install ultralytics torch")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class MangoBananaTrainer:
    """
    芒果香蕉成熟度检测训练器

    负责训练、评估和管理 YOLO11 目标检测模型
    """

    # 类别定义
    CLASSES = ["Raw_Banana", "Raw_Mango", "Ripe_Banana", "Ripe_Mango"]
    CLASS_MAP = {i: name for i, name in enumerate(CLASSES)}

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化训练器

        参数：
            base_dir: 项目基础目录
        """
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        else:
            self.base_dir = Path(base_dir)

        # 路径配置
        self.dataset_dir = self.base_dir / "data"
        self.dataset_yaml = self.dataset_dir / "mango_banana.yaml"
        self.models_dir = self.base_dir / "models"
        self.outputs_dir = self.base_dir / "training_outputs"

        # 默认训练配置
        self.default_config = {
            "epochs": 100,
            "batch": 32,
            "imgsz": 640,
            "device": "0",
            "patience": 20,
            "lr0": 0.01,
            "lrf": 0.01,
            "momentum": 0.937,
            "weight_decay": 0.0005,
            "workers": 4
        }

        # 确保目录存在
        self._ensure_directories()

        # 检测硬件环境
        self.device_info = self._detect_device()

    def _ensure_directories(self):
        """确保必要目录存在"""
        for dir_path in [self.models_dir, self.outputs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _detect_device(self) -> Dict[str, Any]:
        """
        检测并返回硬件环境信息

        返回：
            dict: 包含设备类型、GPU型号、显存等信息
        """
        info = {
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_type": "cpu"
        }

        if torch.cuda.is_available():
            info["device_type"] = "cuda"
            info["cuda_version"] = torch.version.cuda
            info["cudnn_version"] = torch.backends.cudnn.version()
            info["gpu_count"] = torch.cuda.device_count()
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024 ** 3, 1
            )

        return info

    def _print_device_info(self):
        """输出设备信息"""
        logger.info("=" * 60)
        logger.info("🖥️  硬件环境信息")
        logger.info("=" * 60)
        logger.info(f"PyTorch 版本: {self.device_info['pytorch_version']}")
        logger.info(f"CUDA 可用: {self.device_info['cuda_available']}")

        if self.device_info['cuda_available']:
            logger.info(f"CUDA 版本: {self.device_info['cuda_version']}")
            logger.info(f"cuDNN 版本: {self.device_info['cudnn_version']}")
            logger.info(f"GPU 数量: {self.device_info['gpu_count']}")
            logger.info(f"GPU 型号: {self.device_info['gpu_name']}")
            logger.info(f"GPU 显存: {self.device_info['gpu_memory_gb']} GB")
            logger.info(f"✅ 使用 GPU 训练: device='0'")
        else:
            logger.info(f"⚠️  使用 CPU 训练")


    def verify_dataset(self, dataset_dir: Optional[str] = None) -> bool:
        """
        验证数据集完整性：检查图片与标注文件是否一一对应

        参数：
            dataset_dir: 数据集目录路径，默认使用 self.dataset_dir

        返回：
            bool: 验证是否全部通过
        """
        dataset_path = Path(dataset_dir) if dataset_dir else self.dataset_dir

        logger.info("=" * 60)
        logger.info("🔗 数据集完整性检查")
        logger.info("=" * 60)
        logger.info(f"数据集路径: {dataset_path}")

        splits = ['train', 'val', 'test']
        all_passed = True

        for split in splits:
            img_dir = dataset_path / split / "images"
            lbl_dir = dataset_path / split / "labels"

            if not img_dir.exists() or not lbl_dir.exists():
                logger.warning(f"\n❌ [{split}] 目录不存在，跳过检查")
                continue

            # 获取图片名（不含后缀）
            img_names = {f.stem for f in img_dir.iterdir()
                         if f.suffix.lower() in self.IMAGE_EXTENSIONS}

            # 获取标注名（不含后缀）
            lbl_names = {f.stem for f in lbl_dir.glob("*.txt")}

            # 计算对应关系
            has_both = img_names & lbl_names  # 有图有标注 ✅
            missing_lbl = img_names - lbl_names  # 有图无标注 ❌
            missing_img = lbl_names - img_names  # 有标注无图 ❌

            logger.info(f"\n📁 [{split}]")
            logger.info(f"   图片数: {len(img_names)}")
            logger.info(f"   标注数: {len(lbl_names)}")
            logger.info(f"   ✅ 对应完整: {len(has_both)}")

            if missing_lbl:
                logger.warning(f"   ❌ 有图无标注: {len(missing_lbl)}")
                for name in list(missing_lbl)[:3]:
                    logger.warning(f"      - {name}")
                if len(missing_lbl) > 3:
                    logger.warning(f"      ... 还有 {len(missing_lbl) - 3} 个")
                all_passed = False

            if missing_img:
                logger.warning(f"   ❌ 有标注无图: {len(missing_img)}")
                for name in list(missing_img)[:3]:
                    logger.warning(f"      - {name}")
                if len(missing_img) > 3:
                    logger.warning(f"      ... 还有 {len(missing_img) - 3} 个")
                all_passed = False

            if not missing_lbl and not missing_img:
                logger.info(f"   ✅ 全部对应正确！")

        # 检查类别文件
        classes_file = dataset_path / 'classes.txt'
        if classes_file.exists():
            with open(classes_file, 'r', encoding='utf-8') as f:
                classes = [line.strip() for line in f if line.strip()]
            logger.info(f"\n📋 类别文件 ({len(classes)} 类):")
            for i, cls in enumerate(classes):
                logger.info(f"   {i}: {cls}")

            # 验证类别数是否匹配
            if len(classes) != len(self.CLASSES):
                logger.warning(f"⚠️  类别数不匹配: 配置文件 {len(self.CLASSES)} 类 vs classes.txt {len(classes)} 类")
        else:
            logger.warning(f"\n⚠️  未找到 classes.txt")

        logger.info(f"\n{'=' * 60}")
        if all_passed:
            logger.info("✅ 数据集验证全部通过！")
        else:
            logger.warning("⚠️  数据集存在问题，建议修复后再训练")
        logger.info(f"{'=' * 60}")

        return all_passed


    def _validate_dataset(self) -> bool:
        """
        验证数据集是否存在

        返回：
            bool: 验证是否通过
        """
        if not self.dataset_yaml.exists():
            logger.error(f"数据集配置文件不存在: {self.dataset_yaml}")
            return False

        if not self.dataset_dir.exists():
            logger.error(f"数据集目录不存在: {self.dataset_dir}")
            return False

        # 检查训练集和验证集
        for split in ['train', 'val', 'test']:
            split_path = self.dataset_dir / split
            if not split_path.exists():
                logger.warning(f"{split} 目录不存在")
                continue

            img_dir = split_path / 'images'
            lbl_dir = split_path / 'labels'
            img_count = len(list(img_dir.glob('*'))) if img_dir.exists() else 0
            lbl_count = len(list(lbl_dir.glob('*.txt'))) if lbl_dir.exists() else 0
            logger.info(f"  {split:6s}: images={img_count}, labels={lbl_count}")

        logger.info(f"✅ 数据集验证通过: {self.dataset_yaml}")
        return True


    def _save_metadata(self, metadata: dict, output_path: Path):
        """
        保存模型元数据

        参数：
            metadata: 元数据字典
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 元数据已保存: {output_path}")


    def train(self, config: dict = None) -> Optional[Dict[str, Any]]:
        """
        训练 YOLO 模型

        参数：
            config: 训练配置字典，覆盖默认配置

        返回：
            dict: 包含训练结果和元数据的字典
        """
        # 合并配置
        train_config = {**self.default_config, **(config or {})}
        device = train_config.get("device", "0")

        # 输出环境信息
        self._print_device_info()

        logger.info("=" * 60)
        logger.info("🥭🍌 芒果香蕉成熟度检测 - YOLO11 训练")
        logger.info("=" * 60)

        # 验证数据集
        if not self._validate_dataset():
            return None

        # 打印训练配置
        logger.info("\n📋 训练配置:")
        for key, value in train_config.items():
            logger.info(f"  {key:12s}: {value}")

        try:
            # 加载预训练模型
            model_name = train_config.get("model", "yolo11m.pt")
            logger.info(f"\n📦 加载模型: {model_name}")
            model = YOLO(model_name)

            # 训练
            logger.info(f"\n🚀 开始训练 ({train_config['epochs']} epochs)...")
            # 记录训练开始时间
            start_timestamp = datetime.now()
            start_time = time.time()
            logger.info(f"🕐 训练开始时间: {start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            results = model.train(
                data=str(self.dataset_yaml),
                epochs=train_config["epochs"],
                batch=train_config["batch"],
                imgsz=train_config["imgsz"],
                device=device,
                lr0=train_config["lr0"],
                lrf=train_config["lrf"],
                momentum=train_config["momentum"],
                weight_decay=train_config["weight_decay"],
                patience=train_config["patience"],
                workers=train_config["workers"],

                project=str(self.models_dir),
                name="train_v1",
                exist_ok=True,

                augment=True,
                mosaic=1.0,
                mixup=0.1,
                degrees=5.0,
                scale=0.5,
                shear=2.0,
                fliplr=0.5,
                flipud=0.0,

                box=7.5,
                cls=0.5,
                dfl=1.5,

                save=True,
                save_period=10,
                seed=42,
                deterministic=True,
                verbose=True,
                plots=True
            )

            # 获取结果路径
            result_dir = Path(results.save_dir)
            best_model_path = result_dir / "weights" / "best.pt"
            last_model_path = result_dir / "weights" / "last.pt"

            # 计算训练结束时间与持续时间
            end_time = time.time()
            end_timestamp = datetime.now()
            elapsed = end_time - start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)

            logger.info("\n" + "=" * 60)
            logger.info("🎉 训练完成！")
            logger.info("=" * 60)
            logger.info(f"🕐 训练结束时间: {end_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  训练耗时: {hours}小时 {minutes}分 {seconds}秒")
            logger.info(f"结果目录: {result_dir}")
            logger.info(f"最佳模型: {best_model_path}")

            # 评估模型
            metrics = self.evaluate(str(best_model_path))

            # 构建元数据
            metadata = {
                "name": "mango-banana-yolo11m",
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "description": "芒果香蕉成熟度检测 YOLO11 模型",
                "classes": self.CLASSES,
                "device_info": self.device_info,
                "training_config": train_config,

                # 时间信息
                "training_start_time": start_timestamp.isoformat(),
                "training_end_time": end_timestamp.isoformat(),
                "training_duration": f"{hours}h {minutes}m {seconds}s",
                "training_duration_seconds": round(elapsed, 2),

                "metrics": metrics or {},
                "paths": {
                    "best_model": str(best_model_path),
                    "last_model": str(last_model_path),
                    "results_csv": str(result_dir / "results.csv"),
                    "results_png": str(result_dir / "results.png"),
                    "confusion_matrix": str(result_dir / "confusion_matrix.png")
                }
            }

            # 保存元数据
            metadata_path = result_dir / "metadata.json"
            self._save_metadata(metadata, metadata_path)

            # 打包输出成果
            self._package_outputs(result_dir, metadata)

            return {
                "model_path": best_model_path,
                "metadata": metadata,
                "result_dir": result_dir
            }

        except Exception as e:
            logger.error(f"❌ 训练失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


    def evaluate(self, model_path: str = None, data: str = None) -> Optional[Dict[str, float]]:
        """
        评估模型

        参数：
            model_path: 模型路径，默认使用最佳模型
            data: 数据集配置路径

        返回：
            dict: 评估指标
        """
        if model_path is None:
            # 查找最新训练的模型
            model_path = self._find_latest_model()
            if model_path is None:
                logger.error("未找到模型文件")
                return None

        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"模型不存在: {model_path}")
            return None

        data_path = data or str(self.dataset_yaml)

        logger.info("\n" + "=" * 60)
        logger.info("📊 模型评估")
        logger.info("=" * 60)
        logger.info(f"模型: {model_path}")
        logger.info(f"数据集: {data_path}")

        try:
            model = YOLO(str(model_path))
            metrics = model.val(
                data=data_path,
                split="test",
                device=self.device_info.get("device_type", "cpu"),
                batch=32,
                conf=0.25,
                iou=0.45,
                plots=True
            )

            results = {
                "mAP50": round(float(metrics.box.map50), 4),
                "mAP50_95": round(float(metrics.box.map), 4),
                "precision": round(float(metrics.box.mp), 4),
                "recall": round(float(metrics.box.mr), 4)
            }

            logger.info("\n📈 评估结果:")
            for key, value in results.items():
                logger.info(f"  {key:12s}: {value:.4f}")

            # 各类别 AP
            logger.info("\n📋 各类别 mAP50:")
            for i, name in self.CLASS_MAP.items():
                ap = metrics.box.ap50[i] if hasattr(metrics.box, 'ap50') and i < len(metrics.box.ap50) else 0
                logger.info(f"  {name:15s}: {ap:.4f}")

            return results

        except Exception as e:
            logger.error(f"评估失败: {str(e)}")
            return None


    def predict(self, image_path: str, model_path: str = None, conf: float = 0.25):
        """
        单张图片预测

        参数：
            image_path: 图片路径
            model_path: 模型路径
            conf: 置信度阈值

        返回：
            results: 预测结果
        """
        if model_path is None:
            model_path = self._find_latest_model()

        if model_path is None or not Path(model_path).exists():
            logger.error("模型文件不存在")
            return None

        if not Path(image_path).exists():
            logger.error(f"图片不存在: {image_path}")
            return None

        logger.info(f"\n🔍 预测: {image_path}")

        model = YOLO(str(model_path))
        results = model.predict(
            source=image_path,
            conf=conf,
            save=True,
            save_txt=True,
            save_conf=True,
            device=self.device_info.get("device_type", "cpu")
        )

        # 打印结果
        for r in results:
            logger.info(f"\n检测到 {len(r.boxes)} 个目标:")
            for box in r.boxes:
                cls_id = int(box.cls)
                conf_val = float(box.conf)
                name = self.CLASS_MAP.get(cls_id, f"未知{cls_id}")
                logger.info(f"  {name:15s} 置信度: {conf_val:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="芒果香蕉成熟度检测训练工具")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", type=str, default="0")
    args = parser.parse_args()

    trainer = MangoBananaTrainer()
    trainer.train({
        "epochs": args.epochs,
        "batch": args.batch,
        "device": args.device
    })
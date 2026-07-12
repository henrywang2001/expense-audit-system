"""
OCR 工具
提供简单的图片和PDF文本提取功能
"""
import logging
import base64
import os
from typing import Optional, List, Dict, Any
from io import BytesIO

logger = logging.getLogger(__name__)


class OCRTool:
    """
    简单的 OCR 文本提取工具

    支持从图片和 PDF 文件中提取文本。
    注意：这是一个基础实现，生产环境建议使用更专业的 OCR 服务。
    """

    def __init__(self):
        self.supported_formats = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    async def extract_text(self, file_path: str) -> str:
        """
        从文件中提取文本

        Args:
            file_path: 文件路径

        Returns:
            提取的文本内容
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {ext}")

        if ext == ".pdf":
            return await self._extract_pdf_text(file_path)
        else:
            return await self._extract_image_text(file_path)

    async def extract_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """
        从字节流中提取文本

        Args:
            file_bytes: 文件字节数据
            filename: 原始文件名（用于判断文件类型）

        Returns:
            提取的文本内容
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._extract_pdf_text_from_bytes(file_bytes)
        else:
            return self._extract_image_text_from_bytes(file_bytes)

    async def batch_extract(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        批量提取多个文件的文本

        Args:
            file_paths: 文件路径列表

        Returns:
            提取结果列表
        """
        results = []
        for file_path in file_paths:
            try:
                text = await self.extract_text(file_path)
                results.append({
                    "filename": os.path.basename(file_path),
                    "file_path": file_path,
                    "status": "success",
                    "text": text,
                    "text_length": len(text),
                })
            except Exception as e:
                logger.error(f"提取 '{file_path}' 失败: {e}")
                results.append({
                    "filename": os.path.basename(file_path),
                    "file_path": file_path,
                    "status": "failed",
                    "error": str(e),
                })
        return results

    async def _extract_pdf_text(self, file_path: str) -> str:
        """从PDF文件提取文本"""
        text_parts = []

        try:
            # 尝试使用 PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                if text_parts:
                    return "\n\n".join(text_parts)
            except ImportError:
                pass

            # 尝试使用 pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                if text_parts:
                    return "\n\n".join(text_parts)
            except ImportError:
                pass

            # 备选方案：使用 PIL 读取为图片后再处理
            return f"[PDF文件: {os.path.basename(file_path)}] - 需要安装 PyPDF2 或 pdfplumber 进行文本提取"

        except Exception as e:
            logger.warning(f"PDF文本提取失败: {e}")
            return f"[PDF文件: {os.path.basename(file_path)}] - 提取失败: {str(e)}"

    async def _extract_image_text(self, file_path: str) -> str:
        """从图片文件提取文本"""

        try:
            try:
                from PIL import Image
                img = Image.open(file_path)

                # 尝试使用 pytesseract
                try:
                    import pytesseract
                    text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                    if text.strip():
                        return text.strip()
                except ImportError:
                    pass

                # 返回图片基本信息
                return (
                    f"[图片文件: {os.path.basename(file_path)}] "
                    f"尺寸: {img.size[0]}x{img.size[1]}, "
                    f"格式: {img.format} "
                    f"(需要安装 pytesseract 和 tesseract-ocr 进行中文OCR识别)"
                )

            except ImportError:
                pass

            return f"[图片文件: {os.path.basename(file_path)}] - 需要安装 Pillow 进行图片处理"

        except Exception as e:
            logger.warning(f"图片文本提取失败: {e}")
            return f"[图片文件: {os.path.basename(file_path)}] - 提取失败: {str(e)}"

    def _extract_pdf_text_from_bytes(self, file_bytes: bytes) -> str:
        """从PDF字节流提取文本"""
        try:
            from PyPDF2 import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(file_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts) if text_parts else "[PDF文本提取为空]"
        except ImportError:
            return "[需要安装 PyPDF2 进行PDF文本提取]"
        except Exception as e:
            return f"[PDF文本提取失败: {str(e)}]"

    def _extract_image_text_from_bytes(self, file_bytes: bytes) -> str:
        """从图片字节流提取文本"""
        try:
            from PIL import Image
            from io import BytesIO

            img = Image.open(BytesIO(file_bytes))

            try:
                import pytesseract
                text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                return text.strip() if text.strip() else "[图片OCR结果为空]"
            except ImportError:
                return f"[图片: {img.size[0]}x{img.size[1]}, 格式: {img.format}] - 需要安装 pytesseract"

        except ImportError:
            return "[需要安装 Pillow 进行图片处理]"
        except Exception as e:
            return f"[图片处理失败: {str(e)}]"


# 单例
ocr_tool = OCRTool()

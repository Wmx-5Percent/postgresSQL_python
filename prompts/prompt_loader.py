"""
Prompt 加载器 —— 按 用途/版本 加载模板文件并注入变量。

文件结构约定:
    prompts/<category>/<version>/<任意名>.md

每个版本文件夹里只放一个 .md 文件。

用法:
    loader = PromptLoader()
    prompt = loader.load("SQL_filters_generator", "v1", today_str="2026/Feb/27")
"""

import os
import re
from string import Template


class PromptLoader:
    """从 prompts/<category>/<version>/ 下自动找 .md 文件并加载。"""

    # match HTML comment lines
    _HTML_COMMENT_LINE_ = re.compile(r"<!--.*?-->", re.DOTALL)

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = os.path.dirname(os.path.abspath(__file__))
        self.prompts_dir = prompts_dir
    
    @staticmethod
    def _strip_html_comments(text: str) -> str:
        text = PromptLoader._HTML_COMMENT_LINE_.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def load(self, category: str, version: str, **kwargs) -> str:
        version_dir = os.path.join(self.prompts_dir, category, version)

        if not os.path.isdir(version_dir):
            raise FileNotFoundError(
                f"Version directory not found: {version_dir}"
            )

        # 自动查找该目录下的 .md 文件（不写死文件名）
        md_files = [f for f in os.listdir(version_dir) if f.endswith(".md")]

        if len(md_files) == 0:
            raise FileNotFoundError(f"No .md file found in: {version_dir}")
        if len(md_files) > 1:
            raise ValueError(
                f"Multiple .md files found in {version_dir}: {md_files}\n"
                f"Each version folder should contain exactly one .md file."
            )

        file_path = os.path.join(version_dir, md_files[0])

        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
        
        raw = self._strip_html_comments(raw)

        template = Template(raw)
        return template.safe_substitute(**kwargs)

    def list_categories(self) -> list[str]:
        return [
            d for d in os.listdir(self.prompts_dir)
            if os.path.isdir(os.path.join(self.prompts_dir, d))
            and not d.startswith("__")
        ]

    def list_versions(self, category: str) -> list[str]:
        cat_dir = os.path.join(self.prompts_dir, category)
        if not os.path.isdir(cat_dir):
            return []
        return sorted([
            d for d in os.listdir(cat_dir)
            if os.path.isdir(os.path.join(cat_dir, d))
        ])
#!/usr/bin/env python3
"""
Knowledge Base Summary Generator

Features:
- Directory tree structure
- Concise file summaries
- Large file splitting with chunk summaries (JSON array format)
- Concurrent LLM API calls
- Resume capability
- Exponential backoff retry
"""

# Large file splitting configuration
MAX_SUMMARY_TOKENS = 10
MAX_CHUNK_TOKENS = 3000
MIN_CHUNK_TOKENS = 1000
TOKEN_DISPLAY_INTERVAL = 100

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List
import httpx
import tiktoken
from backend.config import settings


class SummaryGenerator:

    def __init__(self):
        self.base_path = Path(settings.knowledge_base)
        self.chunks_dir = Path(settings.knowledge_base_chunks)
        self.output_file = Path(settings.knowledge_base_file_summary)
        self.cache_file = self.output_file.parent / "summary_demo.json"

        # Initialize tokenizer
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
        # Get LLM configuration
        self.provider = settings.api_provider
        self.config = settings.get_provider_config(self.provider)
        
        # API configuration
        self.base_url = self.config.get('base_url', '')
        if '/chat/completions' in self.base_url:
            self.api_url = self.base_url
        else:
            self.api_url = f"{self.base_url}/chat/completions"
        
        self.headers = {
            "Content-Type": "application/json",
            **self.config.get("headers", {})
        }
        if self.config.get("api_key"):
            self.headers["Authorization"] = f"Bearer {self.config['api_key']}"
        
        # Load cache
        self.cache = self._load_cache()

    async def _generate_file_summary(self, file_path: Path, relative_path: str, max_retries: int = 5):
        """
        Generate summary for a single file using LLM
        
        Small files: return string summary
        Large files: return list[dict] chunk summaries
        Support exponential backoff retry
        """
        # Check cache
        if relative_path in self.cache:
            print(f"✅ Using cached summary: {relative_path}")
            return self.cache[relative_path]
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            total_tokens = self._count_tokens(content)
            
            # Check if file needs splitting
            if total_tokens > MAX_CHUNK_TOKENS:
                # Large file: split content by line ranges
                lines = content.split('\n')
                num_chunks = (total_tokens // MAX_CHUNK_TOKENS) + 1
                
                # Build large file splitting prompt with line numbers and token counts
                lines_with_info = []
                cumulative_tokens = 0
                next_mark = 0
                for i, line in enumerate(lines, 1):
                    show_count = cumulative_tokens >= next_mark
                    prefix = f"{i}({cumulative_tokens})" if show_count else str(i)
                    lines_with_info.append(f"{prefix} {line}")
                    if show_count:
                        next_mark = ((cumulative_tokens // TOKEN_DISPLAY_INTERVAL) + 1) * TOKEN_DISPLAY_INTERVAL
                    cumulative_tokens += self._count_tokens(line)
                
                content_with_lines = '\n'.join(lines_with_info)
                
                prompt = f"""- Task: Split the following large file into {num_chunks} small files and provide a content summary for each
- Goal: When users ask questions, let the LLM understand the general content of the file to decide whether to read all the content of that file among many file content summaries
- Length: {MIN_CHUNK_TOKENS} < small file token count < {MAX_CHUNK_TOKENS}, content summary token count < {MAX_SUMMARY_TOKENS}
- Large file: {relative_path}
- Output format: Single-line JSON without code blocks, format like [{{"start": start_line_number, "end": end_line_number, "summary": "content_summary"}}]
- Content summary: Forbidden to include words from file path, low information density words (such as the, it, this, outline, document)
- Important! Do not brutally truncate semantically complete paragraphs and sentences!!!
- Important! Try to put key information directly in the content summary!!!

> Below is the large file content, each line's left number is line number, number in parentheses is cumulative token count

{content_with_lines}

""".strip(); print(prompt)
            else:
                # Small file: generate summary directly
                prompt = f"""- Task: Provide a file content summary
- Goal: When users ask questions, let the LLM understand the general content of the file to decide whether to read all the content of that file among many file content summaries
- Length: Content summary token count < {MAX_SUMMARY_TOKENS}
- File path: {relative_path}
- Content summary: Forbidden to include words from file path, low information density words (such as the, it, this, outline, document)
- Important! Try to put key information directly in the content summary!!!

> Below is the file content

{content}

""".strip(); print(prompt)
            
            messages = [{"role": "user", "content": prompt}]
            
            # Exponential backoff retry
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        payload = {
                            "model": self.config["model"],
                            "messages": messages,
                            "temperature": 0,
                            "stream": False
                        }
                        
                        if "gpt-5" in self.config["model"] or "o1" in self.config["model"]:
                            payload["max_completion_tokens"] = settings.max_tokens
                        else:
                            payload["max_tokens"] = settings.max_tokens
                        
                        response = await client.post(self.api_url, json=payload, headers=self.headers)
                        response.raise_for_status()
                        
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            result = data["choices"][0]["message"].get("content", "").strip()
                            
                            if total_tokens > MAX_CHUNK_TOKENS:
                                # Large file: parse JSON array
                                try:
                                    # Remove possible code block markers
                                    if result.startswith("```"):
                                        result = result.split("\n", 1)[1]
                                    if result.endswith("```"):
                                        result = result.rsplit("\n", 1)[0]
                                    
                                    chunks = json.loads(result)
                                    
                                    # Save chunk files
                                    self._save_chunk_files(file_path, relative_path, chunks, lines)
                                    
                                    # Save to cache
                                    self.cache[relative_path] = chunks
                                    self._save_cache()
                                    
                                    num_chunks = len(chunks)
                                    print(f"✅ Split and summarized ({total_tokens} tokens -> {num_chunks} chunks): {relative_path}")
                                    return chunks
                                except json.JSONDecodeError as e:
                                    print(f"⚠️  Failed to parse JSON for {relative_path}: {e}")
                                    return None
                            else:
                                # Small file: clean newlines and spaces
                                summary = result.replace('\n', ' ').replace('\r', ' ')
                                summary = ' '.join(summary.split())
                                
                                # Copy small file to chunks directory
                                self._copy_small_file(file_path, relative_path)
                                
                                # Save to cache
                                self.cache[relative_path] = summary
                                self._save_cache()
                                
                                print(f"✅ Generated summary ({total_tokens} tokens): {relative_path}")
                                return summary
                        else:
                            print(f"⚠️  Empty response for {relative_path}")
                            return None
                
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    wait_time = (2 ** attempt) * 0.5
                    print(f"⚠️  Attempt {attempt + 1}/{max_retries} failed for {relative_path}: {e}")
                    
                    if attempt < max_retries - 1:
                        print(f"   Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"❌ Max retries reached for {relative_path}")
                        return None
        
        except Exception as e:
            print(f"❌ Error processing {relative_path}: {e}")
            return None

    async def _process_files_with_delay(self, files: List[tuple]) -> Dict[str, str]:
        """
        Process files concurrently with 0.5s delay between requests

        files: [(file_path, relative_path), ...]
        """
        summaries = {}
        tasks = []

        for i, (file_path, relative_path) in enumerate(files):
            # Delayed task launch
            async def delayed_task(fp, rp, delay):
                await asyncio.sleep(delay)
                return rp, await self._generate_file_summary(fp, rp)

            task = delayed_task(file_path, relative_path, i * 0.5)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Task failed: {result}")
            elif result:
                rel_path, summary = result
                if summary:
                    summaries[rel_path] = summary

        return summaries

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))

    def _save_chunk_files(self, file_path: Path, relative_path: str, chunks: List[dict], lines: List[str]):
        """Save chunk files to Knowledge-Base-Chunks directory"""
        # Create directory: Knowledge-Base-Chunks/parent_dir/filename_without_ext/
        file_stem = file_path.stem  # filename without extension
        parent_path = file_path.parent.relative_to(self.base_path)
        chunk_base_dir = self.chunks_dir / parent_path / file_stem
        chunk_base_dir.mkdir(parents=True, exist_ok=True)
        
        for chunk in chunks:
            start = chunk["start"]
            end = chunk["end"]
            
            # Extract lines for this chunk (convert to 0-indexed)
            chunk_lines = lines[start-1:end]
            chunk_content = '\n'.join(chunk_lines)
            
            # Save to file: 1-63.md
            chunk_file = chunk_base_dir / f"{start}-{end}.md"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                f.write(chunk_content)

    def _copy_small_file(self, file_path: Path, relative_path: str):
        """Copy small file to Knowledge-Base-Chunks directory"""
        # Create target path: Knowledge-Base-Chunks/parent_dir/filename.md
        parent_path = file_path.parent.relative_to(self.base_path)
        target_dir = self.chunks_dir / parent_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_file = target_dir / file_path.name
        
        # Copy file
        with open(file_path, 'r', encoding='utf-8') as src:
            content = src.read()
        with open(target_file, 'w', encoding='utf-8') as dst:
            dst.write(content)

    def _collect_all_files(self) -> List[tuple]:
        """Collect all files to process"""
        files = []

        for md_file in self.base_path.rglob("*.md"):
            relative_path = str(md_file.relative_to(self.base_path))
            files.append((md_file, relative_path))

        return files

    def _scan_directory(self, path: Path, prefix: str = "", summaries: Dict[str, str] = None) -> List[str]:
        """
        Recursively scan directory, generate tree structure with summaries

        summaries: {relative_path: summary or chunk info}
        """
        lines = []
        if not path.exists():
            return lines

        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

        for i, item in enumerate(items):
            # Skip cache files
            if item.name.startswith('.'):
                continue

            is_last_item = (i == len(items) - 1)
            connector = "└──" if is_last_item else "├──"

            if item.is_dir():
                # Directory - no trailing slash or colon
                lines.append(f"{prefix}{connector} {item.name}")

                extension = "   " if is_last_item else "│  "
                sub_lines = self._scan_directory(item, prefix + extension, summaries)
                lines.extend(sub_lines)

                # Add separator after directory (if not last)
                if not is_last_item and sub_lines:
                    lines.append(f"{prefix}│")
            else:
                # File
                file_relative = str(item.relative_to(self.base_path))
                file_summary = summaries.get(file_relative, "")

                # Check if chunked file
                if isinstance(file_summary, list):
                    chunks = file_summary

                    # File name without .md extension
                    file_name_no_ext = item.stem
                    lines.append(f"{prefix}{connector} {file_name_no_ext}")

                    # Display each chunk
                    chunk_extension = "   " if is_last_item else "│  "
                    for chunk_idx, chunk in enumerate(chunks):
                        is_last_chunk = (chunk_idx == len(chunks) - 1)
                        chunk_connector = "└──" if is_last_chunk else "├──"

                        start = chunk.get("start", "?")
                        end = chunk.get("end", "?")
                        summary = chunk.get("summary", "")

                        lines.append(f"{prefix}{chunk_extension}{chunk_connector} {start}-{end}.md：{summary}")

                elif file_summary:
                    # Regular file with summary, keep .md extension
                    lines.append(f"{prefix}{connector} {item.name}：{file_summary}")
                else:
                    lines.append(f"{prefix}{connector} {item.name}")

        return lines

    def _load_cache(self) -> Dict[str, str]:
        """Load cached summaries"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")

    async def generate(self):
        """Generate complete knowledge base summary"""
        print("=" * 60)
        print("Knowledge Base Summary Generator")
        print("=" * 60)
        print(f"📁 Knowledge Base Path: {self.base_path}")
        print(f"📄 Output File: {self.output_file}")
        print(f"🤖 LLM Provider: {self.provider}")
        print(f"🎯 Model: {self.config['model']}")
        print("=" * 60)
        
        # 1. Collect all files and calculate total tokens
        print("\n📂 Collecting files...")
        files = self._collect_all_files()
        
        # Calculate knowledge base total tokens
        total_kb_tokens = 0
        for file_path, _ in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_kb_tokens += self._count_tokens(content)
            except Exception as e:
                print(f"⚠️  Failed to read {file_path}: {e}")
        
        print(f"🔍 Found {len(files)} files")
        print(f"📊 Knowledge Base total tokens: {total_kb_tokens:,}")
        
        # 2. Generate file summaries (concurrent with 0.5s delay)
        print("\n🔄 Generating file summaries (concurrent with 0.5s delay)...")
        start_time = time.time()
        file_summaries = await self._process_files_with_delay(files)
        elapsed = time.time() - start_time
        print(f"🎉 Generated {len(file_summaries)}/{len(files)} summaries in {elapsed:.1f}s")
        
        # 3. Build tree structure
        print("\n🌲 Building tree structure...")
        lines = ["."]
        lines.extend(self._scan_directory(self.base_path, summaries=file_summaries))
        
        # 4. Write to file
        print(f"\n💾 Writing to {self.output_file}...")
        output_content = "\n".join(lines)
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # Calculate output tokens and compression ratio
        output_tokens = self._count_tokens(output_content)
        compression_ratio = (output_tokens / total_kb_tokens * 100) if total_kb_tokens > 0 else 0
        
        print("=" * 60)
        print("😊 Summary generation completed!")
        print(f"📊 Total files: {len(files)}")
        print(f"📊 File summaries: {len(file_summaries)}")
        print(f"📄 Output: {self.output_file}")
        print(f"📊 Output file tokens: {output_tokens:,}")
        print(f"📊 Compression ratio: {compression_ratio:.2f}%")
        print("=" * 60)


async def main():
    generator = SummaryGenerator()
    await generator.generate()


if __name__ == "__main__":
    asyncio.run(main())
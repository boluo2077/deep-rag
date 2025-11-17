## 小文件直接摘要

- 任务：给出文件的内容摘要
- 目标：当用户提问时，让LLM了解文件的大概内容，以便在众多文件内容摘要中，决定是否阅读该文件的所有内容
- 长度：Token数<10
- 文件路径：Product-Line-A-Smartwatch-Series/SW-2100-Flagship.md
- 内容摘要：禁止出现文件路径中的词、信息密度低的词（如the、it、this、outline、document）
- 特别注意！尽量把关键信息直接放在内容摘要中！！！

> 以下是文件内容

```markdown
# SW-2100-Flagship: The Apex of Personal Technology

## An Introduction to Uncompromised Excellence

Welcome to the pinnacle of wearable innovation. The SW-2100-Flagship is not merely a timekeeping device; it is a meticulously crafted instrument designed to seamlessly integrate into the fabric of your life, enhancing every moment with unparalleled intelligence, performance, and style. It represents a bold statement of what is possible when cutting-edge technology meets timeless design principles. Conceived for the discerning individual who demands both form and function without compromise, the SW-2100-Flagship is an extension of your intent, a guardian for your health, and a window to your digital world, all resting elegantly on your wrist. Every curve, every material, and every line of code has been thoughtfully considered to deliver an experience that is both profoundly powerful and intuitively simple. This is more than a smartwatch; it is your life, refined.

---

## Design and Craftsmanship: A Symphony of Material and Form

The physical embodiment of the SW-2100-Flagship is a testament to the art of precision engineering and luxurious design. The philosophy behind its creation was to forge a device that feels as magnificent as it performs, a piece of technology that you will be proud to wear in any setting, from the boardroom to the summit of a mountain.
...
```

---

## 大文件分块摘要

- 任务：将以下大文件分割成{tokens//3000+1}个小文件，并给出每个小文件的内容摘要
- 目标：当用户提问时，让LLM了解文件的大概内容，以便在众多文件内容摘要中，决定是否阅读该文件的所有内容
- 长度：1000<小文件Token数<3000，内容摘要Token数<10
- 大文件：Product-Line-A-Smartwatch-Series/SW-2100-Flagship.md
- 输出格式：不使用代码块的单行JSON，格式如[{"start": 起始行号, "end": 终止行号, "summary": "内容摘要"}]
- 内容摘要：禁止出现文件路径中的词、信息密度低的词（如the、it、this、outline、document）
- 特别注意！禁止暴力截断语义完整的段落和句子！！！
- 特别注意！尽量把关键信息直接放在内容摘要中！！！

> 以下是大文件内容，每行左边的数字是行号，行号右边的(数字)是累计Token数

```markdown
1(0) # SW-2100-Flagship: The Apex of Personal Technology
2 
3 ## An Introduction to Uncompromised Excellence
4 
5 Welcome to the pinnacle of wearable innovation. The SW-2100-Flagship is not merely a timekeeping device; it is a meticulously crafted instrument designed to seamlessly integrate into the fabric of your life, enhancing every moment with unparalleled intelligence, performance, and style. It represents a bold statement of what is possible when cutting-edge technology meets timeless design principles. Conceived for the discerning individual who demands both form and function without compromise, the SW-2100-Flagship is an extension of your intent, a guardian for your health, and a window to your digital world, all resting elegantly on your wrist. Every curve, every material, and every line of code has been thoughtfully considered to deliver an experience that is both profoundly powerful and intuitively simple. This is more than a smartwatch; it is your life, refined.
6(196) 
7 ---
8 
9 ## Design and Craftsmanship: A Symphony of Material and Form
10(213) 
11 The physical embodiment of the SW-2100-Flagship is a testament to the art of precision engineering and luxurious design. The philosophy behind its creation was to forge a device that feels as magnificent as it performs, a piece of technology that you will be proud to wear in any setting, from the boardroom to the summit of a mountain.
...
```
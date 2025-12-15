# Crawling Data Project

## Table of Contents
- [Introduction](#introduction)
- [Key features and Learnings](#key-features-and-learnings)
- [File Structure](#file-structure)
- [Installation & Usage](#installation--usage)

___
## Introduction

A Data Engineer project is used for data extraction, handling **200,000** product records. This addresses retry handler, error handler, multi-threading and data field normalization issues during crawling process.
___
## Key features and Learnings

- **Python**.
- **Multi-threading** execution.
- **RESTful API**.
- **Bash Shell**.

___
## File Structure
```
Project2_data/
├── readme.md
├── requirements.txt
├── main_script.sh
│
├── config/
│   ├── config.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── failed/
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── crawler.py
│   ├── cleaner.py
│   ├── splitter.py
│   └── validator.py
│
├── scripts/
│   01_run_crawler.py
│   02_clean_data.py
│   03_split_data.py
│   04_validate_failed.py
│
└── logs/
│
└── output/

```
___


## Installation & Usage
### 1. Clone Repo
~~~
git clone https://github.com/baonguyen-lq/Project2_data.git
~~~

### 2. Navigate to the project directory

~~~
cd Project2_data
~~~

### 3. Run script

~~~
chmod +x main_script.sh
./main_script.sh
~~~



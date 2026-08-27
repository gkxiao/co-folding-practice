# Colabfold MSA
使用 ColabFold API (api.colabfold.com) 生成 MSA 的 .a3m 文件，方法：
```bash
python colabfold_msa.py -h
```
## 1. 生成 MSA

使用 `colabfold_msa.py` 脚本从 FASTA 文件生成 MSA：

```bash
python colabfold_msa.py -f x2.fasta -o x2.a3m
```

**输出示例：**

```
[INFO] MSA 生成配置:
      序列长度: 330
      任务名称: colabfold_job
      输出文件: x2.a3m
      最大等待: 600 秒

[INFO] 正在提交序列到 ColabFold MSA 服务器...
[INFO] 任务提交成功！Job ID: 9iIqzdfPsw2v9y_bJkKeKkauqJFLIRoGeZHVtA
[INFO] 等待服务器处理中，每 5 秒检查一次状态...
[INFO] 处理中... (已等待 30 秒)
[INFO] 处理中... (已等待 60 秒)
[INFO] 处理中... (已等待 90 秒)
[INFO] MSA 比对完成！
[INFO] 正在从 https://api.colabfold.com/result/download/9iIqzdfPsw2v9y_bJkKeKkauqJFLIRoGeZHVtA 下载结果压缩包...
[INFO] 正在解压文件: uniref.a3m
[SUCCESS] MSA 结果已成功保存至: x2.a3m
[INFO] 包含 2967 条序列

[SUCCESS] MSA 生成成功！文件: x2.a3m
```

**生成的 `x2.a3m` 文件：**
- 包含 2967 条同源序列
- 格式为 A3M（带插入/删除信息的多序列比对）
- 直接用于 Boltz 或 OpenFold

---

## 2. 重要：A3M 文件后处理

⚠️ **重要警告**：生成的 `x2.a3m` 文件包含 Windows 换行符（`\r\n`）和可能的空字符（`\x00`），必须清理后才能用于后续结构预测！

### 2.1 问题检查

```bash
# 检查是否有 Windows 换行符 (^M)
cat -v x2.a3m | head -5

# 检查是否有空字符（dos2unix 会报错提示）
dos2unix x2.a3m
```

如果看到每行末尾有 `^M`，说明包含 Windows 换行符；如果报错 `Binary symbol 0x00 found`，说明包含空字符。

### 2.2 后处理命令

```bash
# 移除空字符 (\000) 和 Windows 换行符 (\r)
tr -d '\000\r' < x2.a3m > x2_clean.a3m

# 替换原文件
mv x2_clean.a3m x2.a3m
```

或者一步完成：

```bash
tr -d '\000\r' < x2.a3m > x2_clean.a3m && mv x2_clean.a3m x2.a3m
```

---

## 4. 常见错误及解决

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `KeyError: '\x00'` | 文件包含空字符 | `tr -d '\000\r' < file.a3m > clean.a3m` |
| `KeyError: '\r'` | 文件包含 Windows 换行符 | `tr -d '\r' < file.a3m > clean.a3m` |
| `Skipping binary file` | 文件被识别为二进制 | 同上，清理空字符 |
| MSA 服务器超时 | 网络问题 | 使用代理 `-p http://127.0.0.1:7897` |

---

## 5. 完整流程总结

```bash
# Step 1: 生成 MSA
python colabfold_msa.py -f input.fasta -o input.a3m

# Step 2: 后处理（必须！）
tr -d '\000\r' < input.a3m > input_clean.a3m && mv input_clean.a3m input.a3m
```

> **注意**：`tr -d '\000\r'` 命令会删除所有空字符和回车符，这是使用 ColabFold API 生成的 A3M 文件必须的后处理步骤！

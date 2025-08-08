import os
import re
import torch
import json
import random
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer
import torch.distributed as dist
from utils import parse_uci_move, parse_san_move, san_to_uci, uci_to_san
from vllm import SamplingParams


max_seq_length = 4096
output_dir = "./saved/grpo_train1"

# 修复分布式训练环境变量设置
def setup_distributed():
    # 获取环境变量
    local_rank = int(os.environ.get('LOCAL_RANK', 0))
    rank = int(os.environ.get('RANK', 0))
    world_size = int(os.environ.get('WORLD_SIZE', 1))
    
    # 打印分布式信息用于调试
    print(f"Process info - Local Rank: {local_rank}, Global Rank: {rank}, World Size: {world_size}")
    
    # 初始化分布式训练
    if world_size > 1:
        if not dist.is_initialized():
            # 明确指定使用的GPU设备
            torch.cuda.set_device(local_rank)
            
            # 初始化进程组，指定设备
            dist.init_process_group(
                backend='nccl',
                init_method='env://',  # 使用环境变量初始化
                world_size=world_size,
                rank=rank
            )
            
            print(f"Initialized distributed training on GPU {local_rank}")
        
        return True, local_rank
    
    return False, 0

is_distributed, local_rank = setup_distributed()

def load_model():
    model_path = "/root/paddlejob/qwen3-8b-chess-sft"
    
    # 根据分布式情况选择device_map
    if is_distributed:
        # 分布式模式：先设置设备，再加载模型
        torch.cuda.set_device(local_rank)
        device = f'cuda:{local_rank}'
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map=None,  # 不使用自动设备映射
            low_cpu_mem_usage=True,
        )
        # 将模型移动到指定设备
        model = model.to(device)
        print(f"Model loaded on device: {device}")
        
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto",
        )
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        padding_side="left",
    )
    
    # 设置pad_token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    return model, tokenizer

def load_custom_dataset(file_path="../data/grpo_data.jsonl") -> Dataset:
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            data.append(json.loads(line))

    data = data[:2000]
    processed_data = []
    for item in data:
        system = item["system"]
        prompt = item["prompt"]
        prompt_without_legal_moves = item["prompt_without_legal_moves"]
        if random.random() < 0.5:
            instruction = prompt_without_legal_moves
        else:
            instruction = prompt
        prompt = [
            {"role": "system", "content": system},
            {"role": "user", "content": instruction}
        ]
        processed_data.append({
            "prompt": prompt,
            "fens": item["FEN"],
            "legal_moves": item["legal_moves"],
            "top_moves": item["top_moves"]
        })

    return Dataset.from_list(processed_data)

def get_move(response, fen):
    try:
        uci_move = parse_uci_move(response)
        if not uci_move:
            san_move = parse_san_move(response)
            if san_move:
                uci_move = san_to_uci(san_move, fen)
        return uci_move
    except Exception as e:
        return None
    
def legal_reward_func(completions, fens, legal_moves, **kwargs):
    rewards = []
    for completion, legal_move, current_fen in zip(completions, legal_moves, fens):
        try:
            response_text = completion[0]["content"] if isinstance(completion, list) else completion
            move = get_move(response_text, current_fen)
            if move and move in legal_move:
                reward = 1.0
            else:
                reward = 0.0
            rewards.append(reward)
        except:
            rewards.append(0.0)
    return rewards
    
def optimal_reward_func(completions, fens, top_moves, **kwargs):
    rewards = []
    for completion, top_move, current_fen in zip(completions, top_moves, fens):
        try:
            response_text = completion[0]["content"] if isinstance(completion, list) else completion
            move = get_move(response_text, current_fen)
            if move and move in top_move:
                reward = 1.0
            else:
                reward = 0.0
            rewards.append(reward)
        except:
            rewards.append(0.0)
    return rewards

def best_reward_func(completions, fens, top_moves, **kwargs):
    rewards = []
    for completion, top_move, current_fen in zip(completions, top_moves, fens):
        try:
            response_text = completion[0]["content"] if isinstance(completion, list) else completion
            move = get_move(response_text, current_fen)
            if move and move == top_move[0]:
                reward = 1.0
            else:
                reward = 0.0
            rewards.append(reward)
        except:
            rewards.append(0.0)
    return rewards

def format_reward_func(completions, prompts, **kwargs):
    pattern = r'```\s*.*?\s*```'
    responses = [completion[0]["content"] for completion in completions]
    return [0.5 if re.search(pattern, r, re.DOTALL) else 0.0 for r in responses]

def main():
    print(f"Running in {'distributed' if is_distributed else 'single'} mode")
    if is_distributed:
        print(f"Local rank: {local_rank}, World size: {os.environ.get('WORLD_SIZE', '1')}")
    
    model, tokenizer = load_model()
    dataset = load_custom_dataset()
    
    max_prompt_length = 1024
    training_args = GRPOConfig(
        use_vllm=True,
        vllm_mode="colocate",
        vllm_tensor_parallel_size=8,
        learning_rate=5e-6,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        logging_steps=1,
        bf16=True,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        num_generations=8, 
        max_prompt_length=max_prompt_length,  
        max_completion_length=max_seq_length - max_prompt_length,  
        num_train_epochs=1,
        save_steps=1000,
        report_to="wandb",
        output_dir=output_dir,
        
        # 分布式训练设置
        dataloader_drop_last=True,
        ddp_find_unused_parameters=False,
        remove_unused_columns=False,
        deepspeed="./deepspeed/ds_config.json" if is_distributed else None,
        
        # 添加分布式相关配置
        local_rank=local_rank if is_distributed else -1,
    )

    # 使用自定义trainer
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[
            legal_reward_func,
            optimal_reward_func,
            best_reward_func,
            format_reward_func
        ],
        args=training_args,
        train_dataset=dataset,
    )

    try:
        trainer.train()
    except Exception as e:
        print(f"Training failed with error: {e}")
        if is_distributed and dist.is_initialized():
            dist.destroy_process_group()
        raise
    
    # 只在主进程保存模型
    if not is_distributed or local_rank == 0:
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print(f"Model saved to {output_dir}")
    
    # 清理分布式进程组
    if is_distributed and dist.is_initialized():
        dist.destroy_process_group()

if __name__ == "__main__":
    main()
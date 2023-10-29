#!/usr/bin/env python

import os
import subprocess
import shutil

# https://github.com/turboderp/exllamav2/blob/master/doc/convert.md
# Edit these values below
fp16_model_dir = r"/home/fp16/model/"
quant_dir = r"/home/quants/"
cal_dataset = "0001.parquet" # https://huggingface.co/datasets/wikitext
bits_per_weight = "4.65" # Default = 4.65
head_bits = "8" # Default = 6
gpu_rows = "0" # Default = 0
token_length = "2048" # Default = 2048
measurement_length = "2048" # Default = 2048
# End edit section
quant_dir = os.path.join(quant_dir, f"{os.path.basename(fp16_model_dir)}-{bits_per_weight}bpw-h{head_bits}-exl2")
util_dir = os.path.dirname(os.path.abspath(__file__))
exllama_dir = os.path.dirname(util_dir)
measurement_file = os.path.join(exllama_dir, f"measurement-{os.path.basename(fp16_model_dir)}.json")
conversion_script = os.path.join(exllama_dir, 'util', 'convert_safetensors.py')


def convert_bin_to_safetensors(fp16_model_dir):
    for f in os.listdir(fp16_model_dir):
        if f.endswith('.bin'):
            basename = os.path.splitext(f)[0]
            safetensor_file = f"{basename}.safetensors"
            if os.path.exists(os.path.join(fp16_model_dir, safetensor_file)):
                print(f"Skipping conversion of {f} as the safetensor file already exists")
                continue
            try:
                print(f"converting {basename}.bin to {basename}.safetensor...")
                subprocess.run(['python', conversion_script, os.path.join(fp16_model_dir, f)])
            except Exception as e:
                print(f"Error in converting {f}: {e}")

def clean_up_leftovers(directory):
    shutil.rmtree(os.path.join(directory, 'out_tensor'), ignore_errors=True)
    files_to_remove = ['cal_data.safetensors', 'job.json', 'input_states.safetensors', 'output_states.safetensors']
    for file_name in files_to_remove:
        print(f"Removing {file_name}")
        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

def save_measurement_file():
    if not os.path.exists(measurement_file):
        print("Copying measurement file...")
    try:
        shutil.copy(os.path.join(quant_dir, 'measurement.json'), measurement_file)
    except FileNotFoundError:
        print(f"Failed to find 'measurement.json' in {quant_dir}.")

def copy_model_config():
    print("Copying config files to quant directory...")
    model_files = [f for f in os.listdir(fp16_model_dir) if f.endswith('.json') or f.startswith('tokenizer.')]
    for model_file in model_files:
        shutil.copy(os.path.join(fp16_model_dir, model_file), os.path.join(quant_dir, model_file))

convert_bin_to_safetensors(fp16_model_dir)

if os.path.exists(quant_dir):
    print(f"Target output directory already exists: {quant_dir}")
else:
    print(f"Creating directory {quant_dir}")
    os.makedirs(quant_dir)

os.chdir(exllama_dir)

if os.path.exists(measurement_file):
    print(f"Using previous measurement.json file: {measurement_file}")
    measurement_arg = ['-m', measurement_file]
else:
    print(f"No previous measurement.json file found")
    measurement_arg = []

# Run the conversion
subprocess.run(['python', './convert.py', '-i', fp16_model_dir, '-o', quant_dir, '-c', f'./{cal_dataset}', '-b', bits_per_weight, '-hb', head_bits,'-gr', gpu_rows, '-l', token_length, '-ml', measurement_length] + measurement_arg)

copy_model_config()
save_measurement_file()
clean_up_leftovers(quant_dir)
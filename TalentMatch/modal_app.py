import modal
from modal import App, Image, Volume

app = App("cv-job-matcher")

image = (
    Image.debian_slim()
    .pip_install(
        "torch",
        "transformers",
        "accelerate",
        "bitsandbytes",
        "huggingface_hub",
        "safetensors"
    )
)

secrets = [modal.Secret.from_name("hf-secret")]

GPU = "T4"
CACHE_DIR = "/cache"

hf_cache = Volume.from_name("hf-cache", create_if_missing=True)

BASE_MODEL = "akjindal53244/Llama-3.1-Storm-8B"
LORA_REPO = "LlamaFactoryAI/cv-job-description-matching"


@app.cls(
    image=image.env({"HF_HUB_CACHE": CACHE_DIR}),
    gpu=GPU,
    secrets=secrets,
    volumes={CACHE_DIR: hf_cache},
    timeout=1800,
    min_containers=0
)
class CVJobMatcher:

    @modal.enter()
    def setup(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file

        print("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Loading base model...")
        self.model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            load_in_4bit=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )

        print("Downloading LoRA weights...")
        lora_path = hf_hub_download(
            repo_id=LORA_REPO,
            filename="adapter_model.safetensors"
        )

        lora_weights = load_file(lora_path)
        self._apply_lora(self.model, lora_weights)

        self.model.eval()
        print("Model ready")

    def _apply_lora(self, base_model, lora_state_dict, alpha=16, r=8):
        for name, param in base_model.named_parameters():
            A_key = name + ".lora_A"
            B_key = name + ".lora_B"
            if A_key in lora_state_dict and B_key in lora_state_dict:
                A = lora_state_dict[A_key].to(param.device, param.dtype)
                B = lora_state_dict[B_key].to(param.device, param.dtype)
                param.data += (B @ A) * (alpha / r)

    @modal.method()
    def analyze(self, cv_text: str, job_text: str) -> str:
        import torch

        messages = [
            {
                "role": "system",
                "content": "You are an AI that outputs JSON analyzing CV vs job description."
            },
            {
                "role": "user",
                "content": f"<CV>{cv_text}</CV><job_description>{job_text}</job_description>"
            }
        ]

        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_new_tokens=128,
                temperature=0.7
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

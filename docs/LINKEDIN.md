# LinkedIn post

Launch post for the research note. Image: `output/figures/fig_linkedin.png` (1200 × 1200). The numbers are checked
against `output/tables/` by `tests/test_numbers.py`.

## English

Do open-source LLMs have a home bias?

I asked 12 open-weight models from China, the US, Europe, Thailand and Korea to split a stock portfolio across 8 markets, 240 times each, and checked whether each model gives more to its home market than the other models do.

Short answer: no. A model's home market gets −0.42 pp relative to what other models give it (95% CI −0.59 to −0.25), against an equal weight of 12.5 pp.

What moves the allocation is the user, not the model:
• Tell the model where you live and that market gets +1.88 pp, about 4.4× the size of the home effect.
• Write the prompt in a market's language and that market gets +0.46 pp.
• Every model keeps its cash in US dollars (80–97% of replies), whatever its origin.
• Thai fine-tuning is not a lever: OpenThaiGPT gives Thailand +1.3 pp more than its base model, Typhoon2 gives −1.0 pp.

All 12 models sit far closer to equal weight than to any market-cap benchmark: the US gets 7.9–22.7% of the portfolio, against 75.5% of these eight markets in MSCI ACWI.

The test was pre-registered, the models ran locally on one GPU, and every number in the note rebuilds from the 5,040 archived replies with one command.

📄 Read the note (10 pages, PDF or web): https://thanatchon36.github.io/llm-home-bias/
💾 Code, prompts and every reply: https://github.com/thanatchon36/llm-home-bias
📊 Dataset on Hugging Face: https://huggingface.co/datasets/thanatchon36/llm-home-bias
🔗 DOI: 10.5281/zenodo.23861180

If you use LLMs in investment research, or supervise people who do, I would like to hear what you would test next: other markets, larger models, or different prompts?

#LLM #AIinFinance #HomeBias #OpenSource #Fintech

## ภาษาไทย

LLM แบบ open-source มี home bias ไหม?

ผมให้โมเดล open-weight 12 ตัวจากจีน สหรัฐฯ ยุโรป ไทย และเกาหลี จัดพอร์ตหุ้นข้าม 8 ตลาด ตัวละ 240 ครั้ง แล้วดูว่าแต่ละโมเดลให้น้ำหนักตลาดบ้านตัวเองมากกว่าที่โมเดลอื่นให้หรือไม่

คำตอบสั้น ๆ คือไม่ ตลาดบ้านของโมเดลได้น้ำหนัก −0.42 pp เทียบกับที่โมเดลอื่นให้ (95% CI −0.59 ถึง −0.25) จากน้ำหนักเท่ากันที่ 12.5 pp

สิ่งที่ขยับพอร์ตคือผู้ใช้ ไม่ใช่โมเดล:
• บอกโมเดลว่าคุณอยู่ประเทศไหน ตลาดนั้นได้เพิ่ม +1.88 pp หรือราว 4.4 เท่าของ home effect
• เขียน prompt เป็นภาษาของตลาดนั้น ตลาดนั้นได้เพิ่ม +0.46 pp
• ทุกโมเดลถือเงินสดเป็นดอลลาร์สหรัฐ (80–97% ของคำตอบ) ไม่ว่าจะมาจากประเทศไหน
• การ fine-tune ภาษาไทยไม่ใช่คันโยก: OpenThaiGPT ให้ไทยมากกว่าโมเดลฐาน +1.3 pp แต่ Typhoon2 ให้น้อยกว่า −1.0 pp

ทั้ง 12 โมเดลจัดพอร์ตใกล้น้ำหนักเท่ากันมากกว่า benchmark ตาม market cap มาก: สหรัฐฯ ได้ 7.9–22.7% ของพอร์ต เทียบกับ 75.5% ของ 8 ตลาดนี้ใน MSCI ACWI

งานนี้ pre-register ก่อนรัน โมเดลทุกตัวรันบน GPU เครื่องเดียว และตัวเลขทุกตัวในบทความสร้างใหม่ได้จากคำตอบดิบ 5,040 ชุดด้วยคำสั่งเดียว

📄 อ่านบทความ (10 หน้า PDF หรืออ่านบนเว็บ): https://thanatchon36.github.io/llm-home-bias/
💾 โค้ด prompt และคำตอบทั้งหมด: https://github.com/thanatchon36/llm-home-bias
📊 Dataset บน Hugging Face: https://huggingface.co/datasets/thanatchon36/llm-home-bias
🔗 DOI: 10.5281/zenodo.23861180

ถ้าคุณใช้ LLM ช่วยวิเคราะห์การลงทุน หรือดูแลคนที่ใช้ อยากฟังว่าควรทดสอบอะไรต่อ: ตลาดอื่น โมเดลที่ใหญ่ขึ้น หรือ prompt แบบอื่น?

#LLM #AIinFinance #HomeBias #OpenSource #Fintech

## Alt text for the image

Dot plot titled "On average, open-weight LLMs allocate slightly less, not more, to their home stock market". Twelve open-weight language models, coloured by origin (China, US, Europe, Thailand, Korea), with each model's home-market tilt in percentage points and its 95% confidence interval; values range from −3.5 (Mistral-NeMo-12B) to +1.9 (OpenThaiGPT-1.5-7B). A dashed line and grey band mark the pooled effect of −0.42 pp (95% CI −0.59 to −0.25). The subtitle notes that the investor's stated residence moves that market +1.88 pp, 4.4 times the home effect. Footer: read the note at thanatchon36.github.io/llm-home-bias, DOI 10.5281/zenodo.23861180.

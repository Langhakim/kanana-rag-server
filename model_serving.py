# -*- coding: utf-8 -*-
"""model serving

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1HmY5A2wkyXvExu41tYd6ERMlrrY6jbG7

## llm : kakaocorp/kanana-nano-2.1b-instruct / emb : kanana-emb
"""
# =========================
# 1. JSON 로드 및 문서화
# =========================
import json
import glob
from langchain.schema import Document

docs = []

json_files = glob.glob("/content/drive/MyDrive/KoINISW_Project/metadata-txt-brd/*.json")
for path in json_files:
    with open(path, "r", encoding="utf-8-sig") as f:
        raw_data = json.load(f)
    docs.extend([Document(page_content=item["content"], metadata=item["metadata"]) for item in raw_data])

# =========================
# 2. 텍스트 청크화
# =========================
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=350, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# =========================
# 3. 임베딩 모델 로딩 (kanana embedding)
# =========================
from langchain.embeddings import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={"device": "cuda"}
)

# =========================
# 4. FAISS 벡터스토어 생성
# =========================
from langchain.vectorstores import FAISS

vector_db = FAISS.from_documents(chunks, embedding)

# =========================
# 5. LLM 로딩 (kanana instruct)
# =========================
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain.llms import HuggingFacePipeline
from google.colab import userdata

HUGGING_KEY = userdata.get('HUGGING_KEY')

tokenizer = AutoTokenizer.from_pretrained(
    "kakaocorp/kanana-nano-2.1b-instruct",
    use_auth_token=HUGGING_KEY,
    trust_remote_code=True
)

model = AutoModelForCausalLM.from_pretrained(
    "kakaocorp/kanana-nano-2.1b-instruct",
    use_auth_token=HUGGING_KEY,
    trust_remote_code=True,
    torch_dtype="auto",
    device_map="auto"
)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=1024
)

llm = HuggingFacePipeline(pipeline=pipe)

# =========================
# 6. 프롬프트 템플릿 모음 정의
# =========================
from langchain.prompts import PromptTemplate

common_template = '''당신은 검색된 문서에서만 정보를 추출하여 답변해야 합니다.
검색된 문서 내용에 없는 정보는 추측하지 말고 "해당 정보는 제공되지 않았습니다"라고 답하십시오.
주어진 *.json 문서에 기반하지 않은 추측은 하지 마십시오.
모든 답변은 한번만 출력하도록 하십시오.
'''

storytelling_template = '''
<speak>
  <voice name="echo">
    <prosody rate="fast" pitch="high">
      [최영] 이 나라는 왕명에 의해 움직이는 것이오. 그대가 군을 거느리는 것은 명을 따르기 위함이지, 거역하기 위함이 아니오.
    </prosody>
  </voice>
  <voice name="alloy">
    <prosody rate="medium" pitch="low">
      [이성계] 신은 백성을 먼저 생각하옵니다. 홍수와 전염병이 창궐한 이때, 요동정벌은 곧 멸망을 부르는 길이옵니다.
    </prosody>
  </voice>
</speak>

<speak>
  <voice name="echo">
    <prosody rate="fast" pitch="high">
      [유자광] 조의제문은 선왕을 비방한 글이오. 이를 사초에 기록한 것은 국법을 어긴 행위이니, 엄중히 다스려야 하오.
    </prosody>
  </voice>
  <voice name="alloy">
    <prosody rate="medium" pitch="low">
      [김일손] 이는 스승의 뜻을 기리기 위함이었을 뿐이옵니다. 그 뜻을 왜곡하지 마시옵소서.
    </prosody>
  </voice>
</speak>

<speak>
  <voice name="nova">
    <prosody rate="medium" pitch="high">
      [원균] 이순신 장군, 그대의 독단적인 해전은 조정의 명령을 무시한 행위이오. 책임을 져야 할 것이오!
    </prosody>
  </voice>
  <voice name="alloy">
    <prosody rate="slow" pitch="low">
      [이순신] 저는 바다에서 백성을 지키기 위해 싸웠습니다. 전장은 명분이 아닌 생존의 문제입니다.
    </prosody>
  </voice>
</speak>

<speak>
  <voice name="echo">
    <prosody rate="fast" pitch="high">
      [김상헌] 오랑캐에게 머리를 조아릴 수는 없소. 끝까지 싸워야 하오!
    </prosody>
  </voice>
  <voice name="shimmer">
    <prosody rate="medium" pitch="normal">
      [최명길] 백성의 생명을 지키는 것이 우선이옵니다. 일시적인 굴복이 장기적인 안정을 가져올 것이오.
    </prosody>
  </voice>
</speak>

<speak>
  <voice name="alloy">
    <prosody rate="medium" pitch="low">
      [유계춘] 백성의 고통이 극에 달하였소. 더 이상 참을 수 없어 봉기하였소이다.
    </prosody>
  </voice>
  <voice name="echo">
    <prosody rate="fast" pitch="high">
      [조병갑] 반란은 용서할 수 없소. 엄벌에 처할 것이오!
    </prosody>
  </voice>
</speak>

'''

prompt_templates = {
    "기본": f'''
{common_template}

[지문]
{{context}}

[질문]
{{question}}

아래 템플릿대로 수업자료를 만들어주세요.
[템플릿]
1. 중단원

2. 주요키워드(사건, 인물 등)

3. 요약

4. 추가자료

5. 과제
''',

    "답변만": f'''
{common_template}
답변은 한 문단 이내로 간결하게 작성하세요.
**오직 답변만 출력**하세요. 설명, 요약, 추가정보 없이.

[지문]
{{context}}

[질문]
{{question}}
''',

    "요약전문가": f'''
{common_template}
당신은 교육 요약 전문가입니다. 제공된 지문과 질문을 기반으로 내용을 명확하고 체계적으로 요약 및 정리하세요.

[지문]
{{context}}

[질문]
{{question}}

답변:
''',
    "스토리텔링" : f'''
{common_template}

당신은 시나리오 작가입니다. 제공된 지문과 질문을 기반으로 가장 중요한 인물들을 선택하시오.
당시 역사적 사건과 상황에 대해 주요 인물들의 대화를 이야기 전달 방식으로 대사와 나래이션을 구성하시오.
중학생 교과과정에 맞는 수준에서 아동 및 청소년의 흥미를 이끌 수 있는 구성으로 대본을 작성하시오.
사극의 어체를 활용하여 당대 인물들이 실제로 대화를 나눈듯 하게 몰입할 수 있는 대본을 작성하시오.
인물들의 대사는 아래 [예시] 형식으로 생성하시오
아래는 역사 인물의 대화를 TTS 스타일로 출력하는 예시입니다.
각 인물의 감정과 상황에 따라 voice와 prosody를 다르게 설정합니다.
각 대사는 잘리거나 끊기지 않게 완전한 문장으로 만들어야 합니다.
3회이상 반복되는 불필요한 대사는 생성하지 마세요.
약 15초이내 대화를 작성하시오.

[예시]
{storytelling_template}

[지문]
{{context}}

[질문]
{{question}}

답변:
'''
}

# =========================
# 7. 프롬프트 생성 함수
# =========================
def get_prompt_template(template_str: str) -> PromptTemplate:
    return PromptTemplate(
        input_variables=["context", "question"],
        template=template_str
    )

# =========================
# 8. RAG 체인 빌더 함수
# =========================
from langchain.chains import RetrievalQA

def build_qa_chain(prompt_name="기본"):
    prompt = get_prompt_template(prompt_templates[prompt_name])
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_db.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
        input_key="question",
        chain_type_kwargs={
            "prompt": prompt,
            "document_variable_name": "context"
        }
    )

# =========================
# 9. 실험 예시: 질문 실행
# =========================
qa_chain = build_qa_chain(prompt_name="스토리텔링")

question = "훈민정음 창제에 관해서"
result = qa_chain({"question": question})

print(f'답변 : {result["result"]}')  # 최종 답변

# =========================
# 10. FastAPI 서버 선언
# =========================
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Question(BaseModel):
    query: str

@app.post("/ask")
def ask_question(item: Question):
    result = qa_chain({"question": item.query})
    return {"answer": result["result"]}


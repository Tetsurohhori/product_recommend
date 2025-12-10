"""
このファイルは、最初の画面読み込み時にのみ実行される初期化処理が記述されたファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from uuid import uuid4
import sys
import unicodedata
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
import utils
import constants as ct


############################################################
# 設定関連
############################################################
load_dotenv()

# Streamlit Cloudの場合、secretsから環境変数を設定
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]


############################################################
# 関数定義
############################################################

def initialize():
    """
    画面読み込み時に実行する初期化処理
    """
    # 初期化データの用意
    initialize_session_state()
    # ログ出力用にセッションIDを生成
    initialize_session_id()
    # ログ出力の設定
    initialize_logger()
    # RAGのRetrieverを作成
    initialize_retriever()


def initialize_logger():
    """
    ログ出力の設定
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    if logger.hasHandlers():
        return

    # Streamlit Cloudではファイル書き込みができないため、コンソールに出力
    try:
        os.makedirs(ct.LOG_DIR_PATH, exist_ok=True)
        log_handler = TimedRotatingFileHandler(
            os.path.join(ct.LOG_DIR_PATH, ct.LOG_FILE),
            when="D",
            encoding="utf8"
        )
    except (OSError, PermissionError):
        # ファイル出力ができない場合はStreamHandlerを使用
        log_handler = logging.StreamHandler()
    
    formatter = logging.Formatter(
        f"[%(levelname)s] %(asctime)s line %(lineno)s, in %(funcName)s, session_id={st.session_state.session_id}: %(message)s"
    )
    log_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)


def initialize_session_id():
    """
    セッションIDの作成
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid4().hex


def initialize_session_state():
    """
    初期化データの用意
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []


def initialize_retriever():
    """
    Retrieverを作成
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    if "retriever" in st.session_state:
        return
    
    # Streamlit CloudのシークレットからAPIキーを取得
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        logger.info("APIキーをst.secretsから取得しました")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        logger.info("APIキーを環境変数から取得しました")
    
    # APIキーの存在確認
    if not api_key:
        error_msg = "OPENAI_API_KEYが設定されていません。Streamlit CloudのSecretsを確認してください。"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"APIキーの先頭: {api_key[:10]}...")
    
    loader = CSVLoader(ct.RAG_SOURCE_PATH, encoding="utf-8")
    docs = loader.load()

    # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
    for doc in docs:
        doc.page_content = adjust_string(doc.page_content)
        for key in doc.metadata:
            doc.metadata[key] = adjust_string(doc.metadata[key])

    docs_all = []
    for doc in docs:
        docs_all.append(doc.page_content)

    try:
        embeddings = OpenAIEmbeddings(api_key=api_key)
        logger.info("OpenAIEmbeddingsの初期化完了")
        
        db = Chroma.from_documents(docs, embedding=embeddings)
        logger.info("Chromaデータベースの作成完了")
        
        retriever = db.as_retriever(search_kwargs={"k": ct.TOP_K})
        logger.info("Retrieverの作成完了")
    except Exception as e:
        logger.error(f"Retriever作成中にエラー: {str(e)}")
        raise

    bm25_retriever = BM25Retriever.from_texts(
        docs_all,
        preprocess_func=utils.preprocess_func,
        k=ct.TOP_K
    )
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, retriever],
        weights=ct.RETRIEVER_WEIGHTS
    )

    st.session_state.retriever = ensemble_retriever


def adjust_string(s):
    """
    Windows環境でRAGが正常動作するよう調整
    
    Args:
        s: 調整を行う文字列
    
    Returns:
        調整を行った文字列
    """
    # 調整対象は文字列のみ
    if type(s) is not str:
        return s

    # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
    if sys.platform.startswith("win"):
        s = unicodedata.normalize('NFC', s)
        s = s.encode("cp932", "ignore").decode("cp932")
        return s
    
    # OSがWindows以外の場合はそのまま返す
    return s
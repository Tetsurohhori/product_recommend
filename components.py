"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import logging
import streamlit as st
import constants as ct


############################################################
# 関数定義
############################################################

def display_app_title():
    """
    タイトル表示
    """
    st.markdown(f"## {ct.APP_NAME}")


def display_initial_ai_message():
    """
    AIメッセージの初期表示
    """
    with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
        st.markdown("こちらは対話型の商品レコメンド生成AIアプリです。「こんな商品が欲しい」という情報・要望を画面下部のチャット欄から送信いただければ、おすすめの商品をレコメンドいたします。")
        st.markdown("**入力例**")
        st.info("""
        - 「長時間使える、高音質なワイヤレスイヤホン」
        - 「机のライト」
        - 「USBで充電できる加湿器」
        """)


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar=ct.USER_ICON_FILE_PATH):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
                display_product(message["content"])


def display_product(result):
    """
    商品情報の表示

    Args:
        result: LLMからの回答
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    # デバッグ: resultの内容を確認
    logger.info(f"result type: {type(result)}")
    logger.info(f"result length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
    
    # resultが空でないことを確認
    if not result or len(result) == 0:
        logger.error("resultが空です")
        raise ValueError("商品情報が取得できませんでした")
    
    logger.info(f"result[0] type: {type(result[0])}")
    logger.info(f"result[0].page_content[:200]: {result[0].page_content[:200]}")
    logger.info(f"result[0].metadata: {result[0].metadata}")
    
    # デバッグ用: page_contentとmetadataを画面に表示
    st.write("**デバッグ情報:**")
    st.write(f"page_content: {result[0].page_content[:500]}")
    st.write(f"metadata: {result[0].metadata}")
    
    # LLMレスポンスのテキストを辞書に変換
    product_lines = result[0].page_content.split("\n")
    logger.info(f"product_lines: {product_lines}")
    
    # 空行とコロンを含まない行を除外
    product = {}
    for item in product_lines:
        if item and ": " in item:
            parts = item.split(": ", 1)  # 最大1回だけ分割（値に": "が含まれる場合に対応）
            if len(parts) == 2:
                # キー名の前後の空白を削除
                key = parts[0].strip()
                value = parts[1].strip()
                product[key] = value
    
    logger.info(f"parsed product keys: {list(product.keys())}")
    logger.info(f"product dict: {product}")
    
    # 必要なキーが全て存在するか確認
    required_keys = ['name', 'id', 'price', 'category', 'maker', 'score', 'review_number', 'file_name', 'description', 'recommended_people']
    missing_keys = [key for key in required_keys if key not in product]
    
    if missing_keys:
        logger.error(f"必要なキーが不足しています: {missing_keys}")
        logger.error(f"取得できたキー: {list(product.keys())}")
        raise ValueError(f"商品データに不足があります: {missing_keys}")

    st.markdown("以下の商品をご提案いたします。")

    # 「商品名」と「価格」
    st.success(f"""
            商品名：{product['name']}（商品ID: {product['id']}）\n
            価格：{product['price']}
    """)

    # 「商品カテゴリ」と「メーカー」と「ユーザー評価」
    st.code(f"""
        商品カテゴリ：{product['category']}\n
        メーカー：{product['maker']}\n
        評価：{product['score']}({product['review_number']}件)
    """, language=None, wrap_lines=True)

    # 商品画像
    st.image(f"images/products/{product['file_name']}", width=400)

    # 商品説明
    st.code(product['description'], language=None, wrap_lines=True)

    # おすすめ対象ユーザー
    st.markdown("**こんな方におすすめ！**")
    st.info(product["recommended_people"])

    # 商品ページのリンク
    st.link_button("商品ページを開く", type="primary", use_container_width=True, url="https://google.com")
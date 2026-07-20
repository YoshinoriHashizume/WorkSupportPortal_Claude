# 64ビット版のPythonベースイメージを使用
FROM --platform=linux/amd64 python:3.12-bookworm

# ビルド引数でキャッシュバスティング
ARG CACHEBUST=1

# タイムゾーンを日本時間に設定。
RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "Asia/Tokyo" > /etc/timezone

# bash設定を追加
RUN echo '# Enable bash completion' >> /root/.bashrc && \
    echo 'if [ -f /usr/share/bash-completion/bash_completion ]; then' >> /root/.bashrc && \
    echo '    . /usr/share/bash-completion/bash_completion' >> /root/.bashrc && \
    echo 'elif [ -f /etc/bash_completion ]; then' >> /root/.bashrc && \
    echo '    . /etc/bash_completion' >> /root/.bashrc && \
    echo 'fi' >> /root/.bashrc && \
    echo '# fzf configuration' >> /root/.bashrc && \
    echo 'if [ -f /usr/share/doc/fzf/examples/key-bindings.bash ]; then' >> /root/.bashrc && \
    echo '    source /usr/share/doc/fzf/examples/key-bindings.bash' >> /root/.bashrc && \
    echo 'fi' >> /root/.bashrc && \
    echo '# File selection aliases' >> /root/.bashrc && \
    echo 'alias ff="find . -type f | fzf"' >> /root/.bashrc && \
    echo 'alias fd="find . -type d | fzf"' >> /root/.bashrc && \
    echo 'alias fv="vim \$(find . -type f | fzf)"' >> /root/.bashrc && \
    echo 'alias ll="ls -l"' >> /root/.bashrc && \
    echo '# tree command aliases' >> /root/.bashrc && \
    echo 'alias t="tree"' >> /root/.bashrc && \
    echo 'alias t2="tree -L 2"' >> /root/.bashrc && \
    echo 'alias t3="tree -L 3"' >> /root/.bashrc && \
    echo 'alias td="tree -d"' >> /root/.bashrc

#ログがリアルタイムで表示されるようにする。
ENV PYTHONUNBUFFERED=1

# 必要なパッケージのインストール（uv は公式インストールスクリプトで追加）
RUN apt-get update && apt-get install -y --no-install-recommends\
    iproute2 \
    wget \
    unzip \
    libaio1 libstdc++6 \
    bash-completion \
    fzf tree \
    curl git sudo nano \
    fonts-noto-cjk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && cp /root/.local/bin/uv /usr/local/bin/ \
    && (cp /root/.local/bin/uvx /usr/local/bin/ 2>/dev/null || true)

# Node.js LTS版のインストール
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get update && apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI をグローバルインストール
RUN npm install -g @anthropic-ai/claude-code

# 必要なディレクトリを作成
RUN mkdir -p /django_app/src /django_app/static

# 依存パッケージ（宣言ファイル + 再現用 lock。イメージには lock をインストール）
COPY ./requirements-prod.txt ./requirements-dev.txt ./requirements-docker.txt \
     ./requirements-prod.lock.txt ./requirements-docker.lock.txt /django_app/

# 作業ディレクトリの設定
WORKDIR /django_app

# 以降の RUN でも uv を使えるように PATH を追加（uv は上記 RUN でインストール済み）
ENV PATH="/root/.local/bin:${PATH}"

# uvを使用してパッケージをインストール（pip互換モードで高速インストール）
# 再現性のため lock を正とする（宣言側を変えたら scripts/generate_requirements_lock.sh で再生成）
RUN uv pip install --system --no-cache -r requirements-docker.lock.txt

# Oracle Instant Clientのダウンロードとインストール（64ビット版）
RUN set -eux; \
    mkdir -p /opt/oracle; \
    cd /tmp; \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2390000/instantclient-basic-linux.x64-23.9.0.25.07.zip; \
    unzip -q instantclient-basic-linux.x64-23.9.0.25.07.zip; \
    mv instantclient_23_9 /opt/oracle/instantclient; \
    rm instantclient-basic-linux.x64-23.9.0.25.07.zip

# Oracle Instant Client が参照する libaio.so.1 を用意（自己参照リンクにしない）
RUN set -eux; \
    if [ -e /usr/lib/x86_64-linux-gnu/libaio.so.1.0.1 ]; then \
      ln -sfn /usr/lib/x86_64-linux-gnu/libaio.so.1.0.1 /usr/lib/x86_64-linux-gnu/libaio.so.1; \
    elif [ -e /usr/lib/x86_64-linux-gnu/libaio.so.1.0.2 ]; then \
      ln -sfn /usr/lib/x86_64-linux-gnu/libaio.so.1.0.2 /usr/lib/x86_64-linux-gnu/libaio.so.1; \
    elif [ -e /usr/lib/x86_64-linux-gnu/libaio.so.1t64 ]; then \
      ln -sfn /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /usr/lib/x86_64-linux-gnu/libaio.so.1; \
    fi

# Oracle Clientの環境変数設定
ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH
ENV PATH=/opt/oracle/instantclient:$PATH

# vscodeユーザーを作成（devcontainer用）
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid vscode --shell /bin/bash --create-home vscode \
    && echo vscode ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode

# vscodeユーザーに切り替え（uv は /usr/local/bin にコピー済みのため全ユーザーで利用可能）
USER vscode

# vscodeユーザーのbashrcにPATH、Oracle環境変数、bash-completion、fzf、エイリアスを追加
RUN echo 'export PATH="/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"' >> /home/vscode/.bashrc && \
    echo 'export ORACLE_HOME=/opt/oracle/instantclient' >> /home/vscode/.bashrc && \
    echo 'export LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH' >> /home/vscode/.bashrc && \
    echo '# Enable bash completion' >> /home/vscode/.bashrc && \
    echo 'if [ -f /usr/share/bash-completion/bash_completion ]; then' >> /home/vscode/.bashrc && \
    echo '    . /usr/share/bash-completion/bash_completion' >> /home/vscode/.bashrc && \
    echo 'elif [ -f /etc/bash_completion ]; then' >> /home/vscode/.bashrc && \
    echo '    . /etc/bash_completion' >> /home/vscode/.bashrc && \
    echo 'fi' >> /home/vscode/.bashrc && \
    echo '# fzf configuration' >> /home/vscode/.bashrc && \
    echo 'if [ -f /usr/share/doc/fzf/examples/key-bindings.bash ]; then' >> /home/vscode/.bashrc && \
    echo '    source /usr/share/doc/fzf/examples/key-bindings.bash' >> /home/vscode/.bashrc && \
    echo 'fi' >> /home/vscode/.bashrc && \
    echo '# File selection aliases' >> /home/vscode/.bashrc && \
    echo 'alias ff="find . -type f | fzf"' >> /home/vscode/.bashrc && \
    echo 'alias fd="find . -type d | fzf"' >> /home/vscode/.bashrc && \
    echo 'alias fv="vim \$(find . -type f | fzf)"' >> /home/vscode/.bashrc && \
    echo 'alias ll="ls -l"' >> /home/vscode/.bashrc && \
    echo '# tree command aliases' >> /home/vscode/.bashrc && \
    echo 'alias t="tree"' >> /home/vscode/.bashrc && \
    echo 'alias t2="tree -L 2"' >> /home/vscode/.bashrc && \
    echo 'alias t3="tree -L 3"' >> /home/vscode/.bashrc && \
    echo 'alias td="tree -d"' >> /home/vscode/.bashrc

# rootユーザーに戻る
USER root

# ホストマシンのファイルをコンテナにコピー
COPY ./src/ /django_app/src/
COPY ./entrypoint.sh /django_app/

# entrypoint.shに実行権限を付与
RUN chmod 755 /django_app/entrypoint.sh

# vscodeユーザーに適切な権限を付与
# .claude ディレクトリを事前に作成（Claude Code用）
RUN mkdir -p /home/vscode/.claude && \
    chown -R vscode:vscode /django_app /home/vscode

# PYTHONPATH設定
ENV PYTHONPATH=/django_app/src:$PYTHONPATH

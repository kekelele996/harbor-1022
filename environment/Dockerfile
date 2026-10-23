# 基础镜像按 digest 锁定；镜像已包含 Python、Node.js、网络工具与 Claude Code 启动依赖。
FROM adminfather/benzhi-claude-code2:20260919@sha256:6bc4ad09b1c450579b25e61e7c797328ebaf4ac4eb086c078d2ec1e9f7742046

# 镜像默认用户是 node，入口脚本会等待交互参数；Harbor 需要 root 和常驻命令。
USER root

# 清空基础镜像自带的 Anthropic 网关配置，避免覆盖运行时的模型连接参数。
ENV ANTHROPIC_BASE_URL="" \
    ANTHROPIC_MODEL="" \
    ANTHROPIC_DEFAULT_OPUS_MODEL="" \
    ANTHROPIC_DEFAULT_SONNET_MODEL="" \
    ANTHROPIC_DEFAULT_HAIKU_MODEL="" \
    CLAUDE_CODE_SUBAGENT_MODEL=""

ENTRYPOINT []
CMD ["sleep", "infinity"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# runner 由 Harbor 用于解题和测试入口；评分进程仍以 root 运行。
RUN printf 'runner:x:1001:1001::/home/runner:/bin/bash\n' >> /etc/passwd \
    && printf 'runner:x:1001:\n' >> /etc/group \
    && mkdir -p /home/runner \
    && chown -R 1001:1001 /home/runner \
    && ln -sf /usr/bin/python3 /usr/local/bin/python3

WORKDIR /app
COPY app/ /app/
RUN chown -R runner:runner /app

FROM alpine/git:latest

# Install additional tools
RUN apk add --no-cache \
    openssh-client \
    coreutils \
    netcat-openbsd

WORKDIR /git-cache

# Copy the fetch script
COPY apps/git_cache/fetch.sh /usr/local/bin/fetch.sh
RUN chmod +x /usr/local/bin/fetch.sh

# Create ssh directory for potential SSH keys
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Set up known hosts to avoid SSH prompts
RUN ssh-keyscan -t rsa,ecdsa,ed25519 github.com gitlab.com bitbucket.org >> /root/.ssh/known_hosts 2>/dev/null || true

ENTRYPOINT ["sh", "/usr/local/bin/fetch.sh"]
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"
ZSH_TMUX_AUTOSTART=true

plugins=(git zsh-syntax-highlighting zsh-autosuggestions nvm tmux)

source $ZSH/oh-my-zsh.sh

if [ -x "$(command -v colorls)" ]; then
    alias ls="colorls"
    alias la="colorls -al"
fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
# alias y="yarn"
# alias yd="yarn start:dev"
# alias k="kubectl"
# alias t="tilt"
# alias ds="sudo service docker start"
# alias ms="minikube start --force --driver=docker"
# alias mk="minikube"
# alias ya="yd auth-service"
# alias yc="yd config-service"
# alias ym="yd member-service"
# alias ym="yd member-service"

# K8S #
# function kenv(){
#   find $HOME/projects/ill/scripts -type f | \
#   fzf | awk '{print $1}' | \
#   xargs -o -I % bash %
# }

# function klogs(){
#   kubectl get pods --no-headers | \
#   fzf | awk '{print $1}' | \
#   xargs -o -I % kubectl logs -f %
# }

# function kns(){
#   kubectl get namespace --no-headers | \
#   fzf | awk '{print $1}' | \
#   xargs -o -I % kubectl config set-context --current --namespace=%
# }

# function kwatch(){
#   kubectl get namespace --no-headers | \
#   fzf | awk '{print $1}' | \
#   xargs -o -I % kubectl get pods -w %
# }

# function ksh(){
#   local kubeconfig
#   kubepod=$(kubectl get po | fzf | awk '{print $1}')
#   if [[ -n "$kubepod" ]]; then
#     kubectl exec -it "$kubepod" -- sh
#   fi
# }

# function kdel(){
#   kubectl get pods --no-headers | \
#   fzf | awk '{print $1}' | \
#   xargs -o -I % kubectl delete po %
# }
# ------------------------------- #

alias vport="sudo lsof -nP -iTCP -sTCP:LISTEN"
# Docker #
alias dps="docker ps"
alias drmv="docker rmi $(docker images -a -q)"
alias drmc="docker rm $(docker ps -a -f status=exited -q)"
alias chmodAll="sudo chown -R $USER *"

# scp hoangvh@35.240.149.182:/home/deploy/backup/dump_17-08-2023_06_44_30.sql ../backup/
# alias postgresDump="docker exec -t postgres_db pg_dumpall -c -U postgres > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql"
# alias postgresRestore="cat your_dump.sql | docker exec -i your-db-container psql -U postgres"

function dpush(){
  docker images -a | \
  fzf | awk '{print $1}' | \
  xargs -o -I % docker save % | ssh -C -i ~/.ssh/hoangStaging hoangvh@35.240.149.182 docker load
}

function dlogs(){
  docker ps | \
  fzf | awk '{print $1}' | \
  xargs -o -I % docker logs -f % 
}

function drvol(){
  docker volume list | \
  fzf | awk '{print $1}' | \
  xargs -n2 docker volume rm -f %
}

function dc-up(){
  find $PWD -name 'docker-compose.*.yml' -type f | \
  fzf | awk '{print $1}' | \
  xargs -o -I % docker-compose -f % up --build -d 
}

function dc-build(){
  find . -type d -wholename './apps/*' ! -path './apps/*/*' | \
  fzf | awk '{print $1}' | \
  xargs -o -I % docker-compose build --no-cache -f % 
}

function dc-down(){
  find $PWD -name 'docker-compose.*.yml' -type f | \
  fzf | awk '{print $1}' | \
  xargs -o -I % docker-compose -f % down
}

# Yarn #
function yd(){
  find . -type d -wholename './apps/*' ! -path './apps/*/*' | \
  fzf | cut -c 8- | awk '{print $1}' | \
  xargs -o -I % yarn run start:dev %
}

function yb(){
  find . -type d -wholename './apps/*' ! -path './apps/*/*' | \
  fzf | cut -c 8- | awk '{print $1}' | \
  xargs -o -I % yarn run build %
}
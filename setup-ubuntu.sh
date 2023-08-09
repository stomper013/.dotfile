#!/bin/bash

# Update system
sudo apt update
sudo apt install docker.io zsh fzf unzip curl ruby-full gcc make 

sudo chmod 666 /var/run/docker.sock

zsh

# Install nodejs and yarn
fnm install --lts
npm install --global yarn

# Install NVM
curl https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash 
nvm install node

# Install Theme Zsh - Oh my Zsh
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
source ~/.zshrc

# Install Zsh Syntax Hight-Light
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# Install Zsh Auto Suggestion
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# Install Colorls
sudo gem install colorls

# Add plugins
plugins=( git zsh-syntax-highlighting zsh-autosuggestions )
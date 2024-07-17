echo push $1
#sshpass -p 'x#XdZa4;z2UJ_' ssh ubuntu@101.43.17.243 mkdir $2
sshpass -p 'x#XdZa4;z2UJ_' scp -r $1 ubuntu@101.43.17.243:/home/ubuntu/


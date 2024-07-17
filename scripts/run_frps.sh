sshpass -p 'x#XdZa4;z2UJ_' scp ./generated/frps.toml ubuntu@101.43.17.243:/home/ubuntu
sshpass -p 'x#XdZa4;z2UJ_' ssh ubuntu@101.43.17.243 'sudo pkill -f frps'
echo 'start......'
sshpass -p 'x#XdZa4;z2UJ_' ssh ubuntu@101.43.17.243 'sudo ./frps -c ./frps.toml &> out.txt &'
echo 'end.......'

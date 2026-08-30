The default aws storage was 8GiB but due to it being insufficient we increased it to 20GiB from GUI.

Then we increased the pariticion size using following commands


```cmd
# to viz the partition sizes
lsblk 


# following command grow partition 1 nvme0n1p1
sudo growpart /dev/nvme0n1 1

# then we increase the filesytems using
sudo resize2fs /dev/nvme0n1p1
```

Then we reinstalled requirements.txt


## AWS EBS size

We need more than 20GB. Tested 30GB which works not 24GB

```cmd
(env) ubuntu@ip-172-31-47-12:~/WalkingMeditationServer$ df -h
Filesystem       Size  Used Avail Use% Mounted on
/dev/root         29G   18G   11G  62% /
tmpfs            3.8G     0  3.8G   0% /dev/shm
tmpfs            1.6G  1.1M  1.6G   1% /run
tmpfs            5.0M     0  5.0M   0% /run/lock
efivarfs         128K  3.6K  120K   3% /sys/firmware/efi/efivars
/dev/nvme0n1p16  881M   89M  730M  11% /boot
/dev/nvme0n1p15  105M  6.2M   99M   6% /boot/efi
tmpfs            779M   12K  779M   1% /run/user/1000
```
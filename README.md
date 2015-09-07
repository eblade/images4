# images4


## Installation

Requirements:

* pillow
* sqlalchemy
* bottle


Before installing pillow (PIL):

Make sure you have `libjpeg-dev` that provides for JPEG decoding:

``` bash
sudo apt install libjpeg-dev # or yum install libjpeg-devel or whatever
sudo pip3 install pillow
```

If you still don't have the JPEG decoder:

``` bash
sudo pip3 install -I --no-cache-dir pillow
```

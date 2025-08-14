target = image.sif
base = docker://tensorflow/tensorflow:2.19.0-gpu
tmpsif = tensorflow.sif

all: $(target)

$(target): $(target:.sif=.def) ../setup.sh ../requirements.txt $(tmpsif)
	apptainer build --force --fakeroot $@ $<

$(tmpsif): Makefile
	apptainer build --force --fakeroot $@ $(base)

clean:
	rm -f *.sif

# ---------------------------------------
# yoloのパッケージだけを更新できるようにするため
# target = image.sif
# base = docker://tensorflow/tensorflow:2.19.0-gpu
# tmpsif = tensorflow.sif
# yolotarget = yolo.sif

# all: $(yolotarget)

# $(yolotarget): image.sif yolo.def
# 	apptainer build --force --fakeroot yolo.sif yolo.def

# $(target): $(target:.sif=.def) ../setup.sh ../requirements.txt $(tmpsif)
# 	apptainer build --force --fakeroot $@ $<

# $(tmpsif): Makefile
# 	apptainer build --force --fakeroot $@ $(base)

# clean:
# 	rm -f *.sif
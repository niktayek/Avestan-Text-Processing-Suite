data_dir := './data/escriptorium/export_doc58_lb2_flip_01_alto_20250521134450'

compile:
	poetry run ketos compile \
		--workers 8 \
		--format-type xml \
		--output $(data_dir)/dataset.arrow \
		$(data_dir)/*.xml

########################################################################################
# Recognition train and test
########################################################################################

rec_model_dir := './models/recognition'
#rec_prev_model := 'Sephardi_01.mlmodel'
#rec_prev_model := 'manuscript_4000/attempt_04/model_best.mlmodel'
rec_prev_model := 'manuscript_lb2/attempt_21/model_best.mlmodel'
rec_next_model := 'manuscript_lb2/attempt_22'
rec_learning_rate := 0.00001
# start learning rate at 0.0001 and decrease by 10% every 10 epochs

train-rec:
	mkdir -p $(rec_model_dir)/$(rec_next_model)
	poetry run ketos train \
		--workers 8 \
		--output $(rec_model_dir)/$(rec_next_model)/model \
		--load $(rec_model_dir)/$(rec_prev_model) \
		--resize new \
		--epochs 100 \
		--min-epochs 20 \
		--lrate $(rec_learning_rate) \
		--format-type binary \
		$(data_dir)/dataset.arrow

test-rec:
	poetry run ketos test \
		--model $(rec_model_dir)/$(rec_prev_model) \
		--workers 8 \
		--format-type binary \
		$(data_dir)/dataset.arrow

########################################################################################
# Segmentation train
########################################################################################

seg_model_dir := './models/segmentation'
seg_next_model := 'manuscript_0090/attempt_01'
seg_prev_model := '0088_flip_seg2.mlmodel'

train-seg:
	mkdir -p $(seg_model_dir)/$(seg_next_model)
	poetry run ketos --verbose segtrain -cl \
		--workers 1 \
		--threads 1 \
		--output $(seg_model_dir)/$(seg_next_model)/model \
		--format-type alto \
		$(data_dir)/*.xml
#		--epochs 100 \
#		--min-epochs 20 \


########################################################################################
# OCR run
########################################################################################

ocr:
	poetry run kraken \
		--verbose \
		--batch-input './data/Test_40/*.png' \
		--suffix _ocr.txt \
		segment -bl --model ./models/segmentation/0088_flip_seg2.mlmodel \
		ocr --model ./models/recognition/manuscript_0040/model_best.mlmodel
#		--suffix _ocr.xml \
#		--alto \

########################################################################################
# Git Repository Initialization
########################################################################################

init:
	git submodule update --init --recursive
	poetry install --no-root

########################################################################################
# eScriptorium
########################################################################################

start-escriptorium:
	cd escriptorium && docker compose up

stop-escriptorium:
	cd escriptorium && docker compose down

########################################################################################
# Install repo
########################################################################################

setup:
	asdf plugin add python
	asdf plugin add poetry
	asdf install
	git submodule update --init --recursive
	poetry install --no-root

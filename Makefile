data_dir := './data/escriptorium/export_doc29_0093_ab5_pagexml_20250226181451'

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
rec_prev_model := 'manuscript_0093/attempt_09/model_best.mlmodel'
rec_next_model := 'manuscript_0093/attempt_10'
rec_learning_rate := 0.00003
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
	poetry run ketos segtrain \
		--workers 1 \
		--threads 1 \
		--output $(seg_model_dir)/$(seg_next_model)/model \
		--epochs 100 \
		--min-epochs 20 \
		--format-type page \
		$(data_dir)/*.xml

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
	cd escriptorium && sudo docker compose up

stop-escriptorium:
	cd escriptorium && sudo docker compose down

########################################################################################
# Install repo
########################################################################################

setup:
	asdf install
	git submodule update --init --recursive
	poetry install --no-root

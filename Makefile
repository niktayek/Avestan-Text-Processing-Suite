########################################################################################
# OCR train and test
########################################################################################

data_dir := './data/escriptorium/export_doc7_0088_flip_alto_202502171531'
model_dir := './models/recognition'
#prev_model := 'Sephardi_01.mlmodel'
prev_model := 'manuscript_0088/attempt_12/model_best.mlmodel'
next_model := 'manuscript_0088/attempt_15'
learning_rate := 0.000049
# start learning rate at 0.0001 and decrease by 10% every 10 epochs

compile:
	poetry run ketos compile \
		--workers 8 \
		--format-type xml \
		--output $(data_dir)/dataset.arrow \
		$(data_dir)/*.xml

train:
	mkdir -p $(model_dir)/$(next_model)
	poetry run ketos train \
		--workers 8 \
		--output $(model_dir)/$(next_model)/model \
		--load $(model_dir)/$(prev_model) \
		--resize new \
		--epochs 100 \
		--min-epochs 20 \
		--lrate $(learning_rate) \
		--format-type binary \
		$(data_dir)/dataset.arrow

test:
	poetry run ketos test \
		--model $(model_dir)/$(prev_model) \
		--workers 8 \
		--format-type binary \
		$(data_dir)/dataset.arrow

########################################################################################
# OCR run
########################################################################################

ocr:
	poetry run kraken \
		--batch-input './data/tmp/*.png' \
		--suffix _ocr.txt \
		segment -bl --model ./models/segmentation/0088_flip_seg2.mlmodel \
		ocr --model ./models/recognition/manuscript_0088/model_best.mlmodel
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

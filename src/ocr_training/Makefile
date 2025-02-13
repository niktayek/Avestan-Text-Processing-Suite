data_dir := '../../data/escriptorium/export_doc5_0040_flip_alto_202502131410'
model_dir := '../../models'
prev_model := 'Sephardi_01.mlmodel'
#prev_model := '2000_4030_mirrored_rec_1.mlmodel'
#prev_model := 'manuscript_0090/attempt_02/model_best.mlmodel'
next_model := 'manuscript_0040/attempt_01'
learning_rate := 0.0001
# start learning rate at 0.0001 and decrease by 10% every 10 epochs


compile:
	ketos compile \
		--workers 8 \
		--format-type xml \
		--output $(data_dir)/dataset.arrow \
		$(data_dir)/*.xml

train:
	mkdir -p $(model_dir)/$(next_model)
	ketos train \
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
	ketos test \
		--model $(model_dir)/$(prev_model) \
		--workers 8 \
		--format-type binary \
		$(data_dir)/dataset.arrow

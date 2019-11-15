import keras
import numpy as np
import tensorflow as tf
from glob import glob
import pandas as pd
from tqdm import tqdm
import keras.backend as K
from keras.utils import np_utils
from keras.models import load_model

class Ablation():
	"""
	Layer importance analysis by ablating each featuremaps 
	in a specific layer

	"""

	def __init__(self, model, weights_pth, metric, layer_name, test_image, gt, classes, nclasses=4):
		"""
		model       : keras model architecture (keras.models.Model)
		weights_pth : saved weights path (str)
                metric      : metric to compare prediction with gt, for example dice, CE
                layer_name  : name of the layer which needs to be ablated
                test_img    : test image used for ablation
                gt          : ground truth for comparision
                classes     : class informatiton which needs to be considered, class label as 
				key and corresponding required values 
				in a tuple: {'class1': (1,), 'whole': (1,2,3)}
                nclasses    : number of unique classes in gt
		"""		
		self.model = model
		self.weights = weights_pth
		self.metric = metric
		self.test_image = test_image
		self.layer = layer_name
		self.gt = gt
		self.classinfo = classes
		self.nclasses = nclasses


	def ablate_filter(self, step):
                """
		step : skip factor for feature map consideration (int)

 		"""
		layer_idx = 0
		for idx, layer in enumerate(self.model.layers):
			if layer.name == self.layer:
				filters_to_ablate = np.arange(0, layer.get_weights()[0].shape[-1], step)
				layer_idx = idx
		            
		#print('Layer = %s' %self.model.layers[self.layer].name)
		self.model.load_weights(self.weights, by_name = True)

		#predicts each volume and save the results in np array
		prediction_unshaped = self.model.predict(self.test_image, batch_size=1, verbose=0)

		dice_json = {}
		dice_json['feature'] = []
		for class_ in self.classinfo.keys():
			dice_json[class_] = []

		for j in tqdm(filters_to_ablate):
			#print('Perturbed_Filter = %d' %j)
			self.model.load_weights(self.weights, by_name = True)
			layer_weights = np.array(self.model.layers[layer_idx].get_weights())

			occluded_weights = layer_weights.copy()
			occluded_weights[0][:,:,:,j] = 0
			occluded_weights[1][j] = 0

			self.model.layers[layer_idx].set_weights(occluded_weights)			
			prediction_unshaped_occluded = self.model.predict(self.test_image,batch_size=1, verbose=0) 

			dice_json['feature'].append(j)
			for class_ in self.classinfo.keys():
				dice_json[class_].append(self.metric(np_utils.to_categorical(self.gt, num_classes=self.nclasses), 
			        				np_utils.to_categorical(prediction_unshaped.argmax(axis = -1), 
											num_classes=self.nclasses), self.classinfo[class_]) - \
					     		self.metric(np_utils.to_categorical(self.gt, num_classes=self.nclasses), 
			        					np_utils.to_categorical(prediction_unshaped_occluded.argmax(axis = -1), 
											num_classes=self.nclasses), self.classinfo[class_]))


		df = pd.DataFrame(dice_json)
		return df

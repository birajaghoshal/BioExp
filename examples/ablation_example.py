import keras
import numpy as np
import tensorflow as tf
from keras.models import load_model
import pandas as pd
from glob import glob
import sys
import os
sys.path.append('..')
from BioExp.helpers import utils
from BioExp.spatial import ablation
from losses import *
import pickle
from lucid.modelzoo.vision_base import Model
from BioExp.concept.feature import Feature_Visualizer
from tqdm import tqdm

seq = 'flair'
model_pb_path = '../../saved_models/model_{}/model.pb'.format(seq)	
model_path = '../../saved_models/model_{}/model-archi.h5'.format(seq)
weights_path = '../../saved_models/model_{}/model-wts-{}.hdf5'.format(seq, seq)


def dice_(y_true, y_pred):
#computes the dice score on two tensors

	sum_p=K.sum(y_pred,axis=0)
	sum_r=K.sum(y_true,axis=0)
	sum_pr=K.sum(y_true * y_pred,axis=0)
	dice_numerator =2*sum_pr
	dice_denominator =sum_r+sum_p
	#print(K.get_value(2*sum_pr), K.get_value(sum_p)+K.get_value(sum_r))
	dice_score =(dice_numerator+K.epsilon() )/(dice_denominator+K.epsilon())
	return dice_score

def metric(y_true, y_pred):
#computes the dice for the whole tumor

	y_true_f = K.reshape(y_true,shape=(-1,4))
	y_pred_f = K.reshape(y_pred,shape=(-1,4))
	y_whole=K.sum(y_true_f[:,1:],axis=1)
	p_whole=K.sum(y_pred_f[:,1:],axis=1)
	dice_whole=dice_(y_whole,p_whole)
	return dice_whole

def dice_label_metric(y_true, y_pred, label):
#computes the dice for the enhancing region
	
	y_true_f = K.reshape(y_true,shape=(-1,4))
	y_pred_f = K.reshape(y_pred,shape=(-1,4))
	y_enh=y_true_f[:,label]
	p_enh=y_pred_f[:,label]
	dice_en=dice_(y_enh,p_enh)
	return dice_en

data_root_path = '../sample_vol/'

model_path = '../../saved_models/model_flair/model-archi.h5'
weights_path = '../../saved_models/model_flair/model-wts-flair.hdf5'

layer = 16

for file in tqdm(glob(data_root_path +'*')[:1]):

	model = load_model(model_path, 
	custom_objects={'gen_dice_loss': gen_dice_loss,'dice_whole_metric':dice_whole_metric,
	'dice_core_metric':dice_core_metric,'dice_en_metric':dice_en_metric})

	test_image, gt = utils.load_vol_brats(file, slicen=78)

	test_image = test_image[:, :, 0].reshape((1, 240, 240, 1))	

	A = ablation.Ablation(model, weights_path, dice_label_metric, layer, test_image, gt)

	ablation_dict = A.ablate_filter(50)

	try:
		values = pd.concat([values, pd.DataFrame(ablation_dict['value'])], axis=1)	
	except:
		values = pd.DataFrame(ablation_dict['value'], columns = ['value'])

mean_value = values.mean(axis=1)

for key in ablation_dict.keys():
	if key != 'value':
		try:
			layer_df = pd.concat([layer_df, pd.DataFrame(ablation_dict[key], columns = [key])], axis=1)	
		except:
			layer_df = pd.DataFrame(ablation_dict[key], columns = [key])

layer_df = pd.concat([layer_df, mean_value.rename('value')], axis=1)	

sorted_df = layer_df.sort_values(['class_list', 'value'], ascending=[True, False])

for i in range(4):
	save_path = '../results/Ablation/unet_{}/layer_{}'.format(seq, layer, i)
	os.makedirs(save_path, exist_ok=True)
	class_df = sorted_df.loc[sorted_df['class_list'] == i]
	class_df.to_csv(save_path +'/class_{}.csv'.format(i))

# print(sorted_df['class_list'], sorted_df['value'])

# K.clear_session()
# # Initialize a class which loads a Lucid Model Instance with the required parameters
# from BioExp.helpers.pb_file_generation import generate_pb

# if not os.path.exists(model_pb_path):
#     print (model.summary())
#     layer_name = 'conv2d_21'# str(input("Layer Name: "))
#     generate_pb(model_path, layer_name, model_pb_path, weights_path)

# input_name = 'input_1' #str(input("Input Name: "))
# class Load_Model(Model):
#     model_path = model_pb_path
#     image_shape = [None, 1, 240, 240]
#     image_value_range = (0, 1)
#     input_name = input_name


# graph_def = tf.GraphDef()
# with open(model_pb_path, "rb") as f:
#     graph_def.ParseFromString(f.read())

# texture_maps = []

# counter  = 0
# for layer_, feature_, class_ in zip(sorted_df['layer'], sorted_df['filter'], sorted_df['class_list']):
#     # if counter == 2: break
#     K.clear_session()
    
#     # Run the Visualizer
#     print (layer_, feature_)
#     # Initialize a Visualizer Instance
#     save_pth = '/media/parth/DATA/datasets/BioExp_results/lucid/unet_{}/ablation/'.format(seq)
#     os.makedirs(save_pth, exist_ok=True)
#     E = Feature_Visualizer(Load_Model, savepath = save_pth)
#     texture_maps.append(E.run(layer = model.layers[layer].name, # + '_' + str(feature_), 
# 						 channel = feature_, transforms = True)) 
#     counter += 1


# json = {'texture':texture_maps, 'class':list(sorted_df['class_list']), 'filter':list(sorted_df['filter']), 'layer':layer, 'importance':list(sorted_df['value'])}


# pickle_path = '/media/parth/DATA/datasets/BioExp_results/lucid/unet_{}/ablation/'.format(seq)
# os.makedirs(pickle_path, exist_ok=True)
# file_ = open(os.path.join(pickle_path, 'all_info'), 'wb')
# pickle.dump(json, file_)

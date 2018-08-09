__author__ = 'Caitrin'
import torch.nn as nn
import BaseNetwork
import torch.nn.functional as F
from .AbstractNetwork import AbstractNetwork
import jsonschema

#TODO: use setters to enforce types/formats/values!
#TODO: make this a base class?
class CNNConfig():
    def __init__(self, mode, filters, filter_size, stride, pool):
        self.mode = mode
        self.filters = filters
        self.filter_size = filter_size
        self.stride = stride
        self.pool = pool

#Where config is of type CNNConfig?
class CNN(BaseNetwork):
    def __init__(self, name, dimensions, config, save_path=None, input_network=None, num_classes=None, activation=activations.Softmax, pred_activation=activations.Softmax, optimizer=optim.Adam, learning_rate=0.001, lr_scheduler=None, stopping_rule='best_validation_error', criterion=None):
        super().__init__(name, dimensions, config, save_path, input_network, num_classes, activation, pred_activation, optimizer, learning_rate, lr_scheduler, stopping_rule, criterion)

    def create_network(self, config, nonlinearity):

        self._network = nn.sequential()

        filters=config.filters
        filter_size=config.filter_size
        stride=config.stride
        pool_mode=config.pool["mode"]
        pool_stride=config.pool["stride"]

        conv_dim = len(filter_size[0])
        lasagne_pools = ['max', 'average_inc_pad', 'average_exc_pad']
        if not all(len(f) == conv_dim for f in filter_size):
            raise ValueError('Each tuple in filter_size {} must have a '
                             'length of {}'.format(filter_size, conv_dim))
        if not all(len(s) == conv_dim for s in stride):
            raise ValueError('Each tuple in stride {} must have a '
                             'length of {}'.format(stride, conv_dim))
        if not all(len(p) == conv_dim for p in pool_stride):
            raise ValueError('Each tuple in pool_stride {} must have a '
                             'length of {}'.format(pool_stride, conv_dim))
        if pool_mode not in lasagne_pools:
            raise ValueError('{} pooling does not exist. '
                             'Please use one of: {}'.format(pool_mode, lasagne_pools))

        print("Creating {} Network...".format(self.name))
        if self.input_network is None:
            print('\tInput Layer:')
            self.input_dim = self.input_dimensions[1]
            layer = InputUnit(
                              in_channels=self.input_dim,
                              out_channels=self.input_dim,
                              bias=True)
            layer_name = "{}_input".format(self.name)
            self.network.add_module(layer_name, layer)
            print('\t\t{}'.format(layer))
            self.layers.append(layer)
        else:
            for l_name, l in self.input_network['network'].network.named_children():
                self.network.add_module(l_name, l)
            layer = l
            layer_name = l_name
            self.input_dim = layer.out_channels

            print('Appending layer {} from {} to {}'.format(
                self.input_network['layer'],
                self.input_network['network'].name,
                self.name))

        print('\tHidden Layer:')
        for i, (f, f_size, s, p_s) in enumerate(zip(filters,
                                                    filter_size,
                                                    stride,
                                                    pool_stride)):
            layer_name = "{}_conv{}D_{}".format(
                                    self.name, conv_dim, i)
            layer = ConvUnit(
                            conv_dim=conv_dim,
                            in_channels=self.input_dim,
                            out_channels=f,
                            kernel_size=f_size,
                            stride=s,
                            pool_size=p_s,
                            activation=nonlinearity)
            self.network.add_module(layer_name, layer)
            self.layers.append(layer)
            print('\t\t{}'.format(layer))
            self.input_dim = layer.out_channels

        self.create_classification_layer(self.network, self.num_classes, self.pred_activation)
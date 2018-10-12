# coding=utf-8
"""Defines the DenseNet class"""
import torch
import torch.nn as nn

from .basenetwork import BaseNetwork
from .layers import DenseUnit

import logging
from inspect import getfullargspec

logger = logging.getLogger(__name__)


class DenseNetConfig:
    """
    Defines the necessary configuration for a DenseNet.
    """
    def __init__(self, raw_config):
        if 'dense_units' not in raw_config:
            raise KeyError("dense_units must be specified.")

        if not isinstance(raw_config['dense_units'], list):
            raise ValueError("dense_units must be of type list.")

        dense_unit_arg_spec = getfullargspec(DenseUnit)
        dense_unit_arg_spec.args.remove('self')

        # Find the index for where the defaulted values begin
        default_arg_start_index = len(dense_unit_arg_spec.args) - len(dense_unit_arg_spec.defaults)
        default_args = dense_unit_arg_spec.args[default_arg_start_index:]

        # Only look at args that were specified to be overwritten
        override_args = set(default_args).intersection(set(raw_config.keys()))
        # If arguments are specified in lists,
        # check that length corresponds to dense_units
        for arg in override_args:
            if isinstance(raw_config[arg], list):
                if len(raw_config[arg]) != len(raw_config['dense_units']):
                    raise ValueError("{} list must be same length as dense_units.".format(arg))
            else:
                # If a single value is specified, it will be applied to all layers
                raw_config[arg] = [raw_config[arg]] * len(raw_config['dense_units'])
        
        # TODO: Think about moving dimension to config file
        _units_per_layer = list([None] + raw_config['dense_units'])
        _unit_pairs = list(zip(_units_per_layer[:-1], _units_per_layer[1:]))

        self.units = []
        for i, (in_feature, out_feature) in enumerate(_unit_pairs):
            temp_unit = {
                'in_features': in_feature,
                'out_features': out_feature
            }
            for arg in override_args:
                temp_unit[arg] = raw_config[arg][i]
            self.units.append(temp_unit)


class DenseNet(BaseNetwork, nn.Module):
    """
    Subclass of BaseNetwork defining a DenseNet

    """

    def __init__(self, name, dimensions, config, save_path=None, input_network=None, num_classes=None,
                 activation=nn.ReLU(), pred_activation=None, optim_spec={'name': 'Adam', 'lr': 0.001},
                 lr_scheduler=None, early_stopping=None, criter_spec=nn.CrossEntropyLoss()):
        
        nn.Module.__init__(self)
        super(DenseNet, self).__init__(name, dimensions, DenseNetConfig(config), save_path, input_network, num_classes,
                                       activation, pred_activation, optim_spec, lr_scheduler, early_stopping, criter_spec
                                       )

    def _create_network(self, **kwargs):
        self.in_dim = self._dimensions

        if self._input_network and \
            self._input_network.__class__.__name__ == "ConvNet":

            if self._input_network.conv_flat_dim != self.in_dim:
                self.in_dim = self.get_flattened_size(self._input_network)
            else:
                pass

        if self._input_network and \
            self._input_network.__class__.__name__ == "DenseNet":

            if self._input_network.dims[-1] != self.in_dim:
                self.in_dim = self._input_network.dims[-1]
            else:
                pass

        dense_hid_layers = self._config.units
        # Build network
        self.network = self._build_dense_network(
            dense_hid_layers, kwargs['activation'])

        if self._num_classes:
            self.out_dim = self._num_classes
            self._create_classification_layer(
                dense_hid_layers[-1]['out_features'],
                kwargs['pred_activation'])

            if torch.cuda.is_available():
                for module in self.modules():
                    module.cuda()

    def _create_classification_layer(self, dim, pred_activation):
        self.network_tail = DenseUnit(
            in_features=dim,
            out_features=self.out_dim,
            activation=pred_activation)

    def forward(self, x):
        """
        Defines the behaviour of the network.
        If the network is defined with `num_classes` then it is
        assumed to be the last network which contains a classification
        layer/classifier (network tail). The data ('x') will be passed
        through the network and then through the classifier.
        If not, the input is passed through the network and
        returned without passing through a classification layer.
        :param x: input torch.Tensor
        :return: output torch.Tensor
        """
        if self._input_network:
            x = self._input_network(x)

        if self._input_network and \
            self._input_network.__class__.__name__ == "ConvNet":
            x = x.view(-1, self._input_network.conv_flat_dim)

        network_output = self.network(x)

        if self._num_classes:
            class_output = self.network_tail(network_output)
            return class_output
        else:
            return network_output

    def _build_dense_network(self, dense_hid_layers, activation):
        """
        Utility function to build the layers into a nn.Sequential object.
        :param dims: The dimensions
        :return: the dense network as a nn.Sequential object
        """
        # Specify incoming feature size for the first dense hidden layer
        dense_hid_layers[0]['in_features'] = self.in_dim
        dense_layers = []
        for dense_layer_config in dense_hid_layers:
            dense_layer_config['activation'] = activation
            dense_layers.append(DenseUnit(**dense_layer_config))
        dense_network = nn.Sequential(*dense_layers)
        return dense_network

    def __str__(self):
        if self.optim:
            return super(DenseNet, self).__str__() + f'\noptim: {self.optim}'
        else:
            return super(DenseNet, self).__str__()

import torch as t
import torch.nn as nn
import torch.nn.functional as F
from utils.selfModules.highway import Highway
from utils.functional import *
from utils.selfModules.selflstm import self_LSTM


class Encoder(nn.Module):
    def __init__(self, params):
        super(Encoder, self).__init__()

        self.params = params

        self.hw1 = Highway(self.params.sum_depth + self.params.word_embed_size, 2, F.relu)

        self.rnn = self_LSTM(input_size=self.params.word_embed_size + self.params.sum_depth,
                             hidden_size=self.params.encoder_rnn_size,
                             num_layers=self.params.encoder_num_layers,
                             batch_first=True,
                             bidirectional=True)

        self.hw2 = Highway(self.rnn.hidden_size * 2, 2, F.relu)
        self.fc = nn.Linear(self.rnn.hidden_size * 2, self.params.latent_variable_size)

    def forward(self, input):
        """
        :param input: [batch_size, seq_len, embed_size] tensor
        :return: context of input sentenses with shape of [batch_size, latent_variable_size]
        """

        [batch_size, seq_len, _] = input.size()

        input = input.view(-1, self.params.sum_depth + self.params.word_embed_size)
        input = self.hw1(input)
        input = input.view(batch_size, seq_len, self.params.sum_depth + self.params.word_embed_size)

        assert parameters_allocation_check(self), \
            'Invalid CUDA options. Parameters should be allocated in the same memory'

        ''' Unfold rnn with zero initial state and get its final state from last layer
        '''
        _, (_, final_state) = self.rnn(input)

        final_state = final_state.view(self.params.encoder_num_layers, 2, batch_size, self.params.encoder_rnn_size)
        final_state = final_state[-1]
        h_1, h_2 = final_state[0], final_state[1]
        final_state = t.cat([h_1, h_2], 1)

        context = self.hw2(final_state)
        context = F.relu(self.fc(context))

        return context

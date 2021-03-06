import random

import torch

class Train_Network(object):
    def __init__(self, encoder, decoder, index2word, num_layers=1, teacher_forcing_ratio=0):
        self.encoder = encoder
        self.decoder = decoder
        self.index2word = index2word
        self.num_layers = num_layers
        self.SOS_token = 1
        self.EOS_token = 2
        self.use_cuda = torch.cuda.is_available()
        self.teacher_forcing_ratio = teacher_forcing_ratio

    def train(self, input_variables, target_variables, lengths, people, criterion,
              encoder_optimizer=None, decoder_optimizer=None, evaluate=False):

        ''' Pad all tensors in this batch to same length. '''
        input_variables = torch.nn.utils.rnn.pad_sequence(input_variables)
        target_variables = torch.nn.utils.rnn.pad_sequence(target_variables)

        input_length = input_variables.size()[0]
        target_length = target_variables.size()[0]
        batch_size = target_variables.size()[1]

        ''' No need to send optimizers in case of evaluation. '''
        if encoder_optimizer: encoder_optimizer.zero_grad()
        if decoder_optimizer: decoder_optimizer.zero_grad()
        loss = 0

        encoder_hidden = self.encoder.initHidden(batch_size)
        encoder_outputs, encoder_hidden = self.encoder(input_variables, lengths, encoder_hidden)

        decoder_inputs = torch.LongTensor([[self.SOS_token]*batch_size])
        decoder_inputs = decoder_inputs.cuda() if self.use_cuda else decoder_inputs

        # Decoder Unidirectional while Encoder Bidirectional
        decoder_hidden = encoder_hidden[:self.num_layers].view(self.num_layers, batch_size, -1)

        if evaluate:
            decoded_words = [[] for i in range(batch_size)]
            decoder_attentions = torch.zeros(batch_size, target_length, input_length)

            for di in range(target_length):
                decoder_outputs, decoder_hidden, decoder_attention = self.decoder(decoder_inputs, people, decoder_hidden, encoder_outputs)
                loss += criterion(decoder_outputs, target_variables[di])

                decoder_attentions[:, di, :] = decoder_attention.data
                topv, topi = decoder_outputs.data.topk(1)

                for i, ind in enumerate(topi[0]):
                    decoded_words[i].append(self.index2word[ind])

                decoder_inputs = topi.permute(1, 0)
                if self.use_cuda: decoder_inputs = decoder_inputs.cuda()

            return loss.item() / target_length, decoded_words, decoder_attentions

        else:
            use_teacher_forcing = True if random.random() < self.teacher_forcing_ratio else False

            if use_teacher_forcing:
                # Teacher forcing: Feed the target as the next input
                for di in range(target_length):
                    decoder_outputs, decoder_hidden, _ = self.decoder(decoder_inputs, people, decoder_hidden,
                                                                      encoder_outputs, lengths)
                    loss += criterion(decoder_outputs, target_variable[di])
                    decoder_inputs = target_variables[di]  # Teacher forcing

            else:
                # Without teacher forcing: use its own predictions as the next input
                for di in range(target_length):
                    decoder_outputs, decoder_hidden, _ = self.decoder(decoder_inputs, people, decoder_hidden, encoder_outputs)
                    topv, topi = decoder_outputs.data.topk(1)
                    decoder_inputs = topi.permute(1, 0)
                    loss += criterion(decoder_outputs, target_variables[di])

            loss.backward()

            encoder_optimizer.step()
            decoder_optimizer.step()

            return loss.item() / target_length

import argparse
import os
import glob

from bidi.algorithm import get_base_level

from google.protobuf.json_format import MessageToJson

from calamari_ocr.utils.glob import glob_all
from calamari_ocr.ocr.dataset import AbbyyDataSet
from calamari_ocr.ocr import MultiPredictor
from calamari_ocr.ocr.voting import voter_from_proto
from calamari_ocr.proto import VoterParams, Predictions
from calamari_ocr.utils.Abbyy.Writer import XMLWriter


def run(args):
    # checks
    if args.extended_prediction_data_format not in ["pred", "json"]:
        raise Exception("Only 'pred' and 'json' are allowed extended prediction data formats")

    # add json as extension, resolve wildcard, expand user, ... and remove .json again
    args.checkpoint = [(cp if cp.endswith(".json") else cp + ".json") for cp in args.checkpoint]
    args.checkpoint = glob_all(args.checkpoint)
    args.checkpoint = [cp[:-5] for cp in args.checkpoint]

    # create voter
    voter_params = VoterParams()
    voter_params.type = VoterParams.Type.Value(args.voter.upper())
    voter = voter_from_proto(voter_params)

    # load files
    files = glob.glob(args.files)
    dataset = AbbyyDataSet(files,
                           skip_invalid=True,
                           remove_invalid=False,
                           binary=args.binary)

    dataset.load_samples(processes=args.processes, progress_bar=not args.no_progress_bars)

    print("Found {} files in the dataset".format(len(dataset)))
    if len(dataset) == 0:
        raise Exception("Empty dataset provided. Check your files argument (got {})!".format(args.files))

    # predict for all models
    predictor = MultiPredictor(checkpoints=args.checkpoint, batch_size=args.batch_size, processes=args.processes)
    do_prediction = predictor.predict_dataset(dataset, progress_bar=not args.no_progress_bars)

    # output the voted results to the appropriate files
    input_image_files = []

    # creat input_image_files list for next loop
    for page in dataset.book.pages:
        for fo in page.getFormats():
            input_image_files.append(page.imgFile)

    for (result, sample), filepath in zip(do_prediction, input_image_files):
        for i, p in enumerate(result):
            p.prediction.id = "fold_{}".format(i)

        # vote the results (if only one model is given, this will just return the sentences)
        prediction = voter.vote_prediction_result(result)
        prediction.id = "voted"
        sentence = prediction.sentence
        if args.verbose:
            lr = "\u202A\u202B"
            print("{}: '{}{}{}'".format(sample['id'], lr[get_base_level(sentence)], sentence, "\u202C" ))

        output_dir = args.output_dir if args.output_dir else os.path.dirname(filepath)

        sample["format"].text = sentence

        if args.extended_prediction_data:
            ps = Predictions()
            ps.line_path = filepath
            ps.predictions.extend([prediction] + [r.prediction for r in result])
            if args.extended_prediction_data_format == "pred":
                with open(os.path.join(output_dir, sample['id'] + ".pred"), 'wb') as f:
                    f.write(ps.SerializeToString())
            elif args.extended_prediction_data_format == "json":
                with open(os.path.join(output_dir, sample['id'] + ".json"), 'w') as f:
                    # remove logits
                    for prediction in ps.predictions:
                        prediction.logits.rows = 0
                        prediction.logits.cols = 0
                        prediction.logits.data[:] = []

                    f.write(MessageToJson(ps, including_default_value_fields=True))
            else:
                raise Exception("Unknown prediction format.")

    w = XMLWriter(output_dir, os.path.dirname(filepath), dataset.book)
    w.write()

    print("All files written")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--files", type=str, required=True, default="",
                        help="List of the Image Files of the Abbyy Documents")
    parser.add_argument("--checkpoint", type=str, nargs="+", default=[],
                        help="Path to the checkpoint without file extension")
    parser.add_argument("-j", "--processes", type=int, default=1,
                        help="Number of processes to use")
    parser.add_argument("--batch_size", type=int, default=1,
                        help="The batch size during the prediction (number of lines to process in parallel)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print additional information")
    parser.add_argument("--voter", type=str, default="confidence_voter_default_ctc",
                        help="The voting algorithm to use. Possible values: confidence_voter_default_ctc (default), "
                             "confidence_voter_fuzzy_ctc, sequence_voter")
    parser.add_argument("--output_dir", type=str,
                        help="By default the prediction files will be written to the same directory as the given files. "
                             "You can use this argument to specify a specific output dir for the prediction files.")
    parser.add_argument("--extended_prediction_data", action="store_true",
                        help="Write: Predicted string, labels; position, probabilities and alternatives of chars to a .pred (protobuf) file")
    parser.add_argument("--extended_prediction_data_format", type=str, default="json",
                        help="Extension format: Either pred or json. Note that json will not print logits.")
    parser.add_argument("--no_progress_bars", action="store_true",
                        help="Do not show any progress bars")
    parser.add_argument("--binary", action="store_true",
                        help="Works with binary images")

    args = parser.parse_args()

    run(args)

if __name__ == "__main__":
    main()

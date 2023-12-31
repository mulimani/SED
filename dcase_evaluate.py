#import config
import numpy as np
import sed_eval
from dcase_util.containers import metadata


def find_contiguous_regions(activity_array):
    '''
    Taken from dcase_util https://dcase-repo.github.io/dcase_util/index.html, written by Toni Heittola et al.
    '''
    # Find the changes in the activity_array
    change_indices = np.logical_xor(activity_array[1:], activity_array[:-1]).nonzero()[0]

    # Shift change_index with one, focus on frame after the change.
    change_indices += 1

    if activity_array[0]:
        # If the first element of activity_array is True add 0 at the beginning
        change_indices = np.r_[0, change_indices]

    if activity_array[-1]:
        # If the last element of activity_array is True, add the length of the array
        change_indices = np.r_[change_indices, len(activity_array)]

    # Reshape the result into two columns
    return change_indices.reshape((-1, 2))


def process_event(class_labels, frame_probabilities, threshold, hop_length_seconds):
    results = []
    for event_id, event_label in enumerate(class_labels):
        # Binarization
        event_activity = frame_probabilities[event_id, :] > threshold

        # Convert active frames into segments and translate frame indices into time stamps
        event_segments = find_contiguous_regions(event_activity) * hop_length_seconds

        # Store events
        for event in event_segments:
            results.append(
                metadata.MetaDataItem(
                    {
                        'event_onset': event[0],
                        'event_offset': event[1],
                        'event_label': event_label
                    }
                )
            )

    results = metadata.MetaDataContainer(results)

    # Event list post-processing
    results = results.process_events(minimum_event_length=None, minimum_event_gap=0.1)
    results = results.process_events(minimum_event_length=0.1, minimum_event_gap=None)
    return results


def get_SED_results(y_true, y_pred, labels, segment_based_metrics, threshold=0.5, hop_size=1024, sample_rate=32000):

    reference = process_event(labels, y_true.T, threshold, hop_size / sample_rate)
    predicted = process_event(labels, y_pred.T, threshold, hop_size / sample_rate)
    #print(reference)
    segment_based_metrics.evaluate(
        reference_event_list=reference,
        estimated_event_list=predicted
    )
    segment_based_metrics_ER = segment_based_metrics.overall_error_rate()
    segment_based_metrics_f1 = segment_based_metrics.overall_f_measure()
    output = segment_based_metrics.result_report_class_wise()
    test_F1 = segment_based_metrics_f1['f_measure']
    test_ER = segment_based_metrics_ER['error_rate']
    class_wise_metrics = segment_based_metrics.results_class_wise_metrics()
    #segment_based_metrics.reset()
    return output, test_ER, test_F1, class_wise_metrics

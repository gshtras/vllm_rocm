import warnings
from typing import Dict, List, Optional, Sequence, Tuple, Union

from vllm.sequence import Logprob, SampleLogprobs

TokensText = Tuple[List[int], str]


def check_outputs_equal(
    *,
    outputs_0_lst: Sequence[TokensText],
    outputs_1_lst: Sequence[TokensText],
    name_0: str,
    name_1: str,
):
    """
    Compare the two sequences generated by different models, 
    which should be equal.
    """
    assert len(outputs_0_lst) == len(outputs_1_lst)

    for prompt_idx, (outputs_0,
                     outputs_1) in enumerate(zip(outputs_0_lst,
                                                 outputs_1_lst)):
        output_ids_0, output_str_0 = outputs_0
        output_ids_1, output_str_1 = outputs_1

        # The text and token outputs should exactly match
        fail_msg = (f"Test{prompt_idx}:"
                    f"\n{name_0}:\t{output_str_0!r}"
                    f"\n{name_1}:\t{output_str_1!r}")

        assert output_str_0 == output_str_1, fail_msg
        assert output_ids_0 == output_ids_1, fail_msg


TokensTextLogprobs = Tuple[List[int], str, Optional[Union[List[Dict[int,
                                                                    float]],
                                                          SampleLogprobs]]]

# Allow for tokens to be represented as str's rather than IDs
TextTextLogprobs = Tuple[List[str], str, Optional[Union[List[Dict[str, float]],
                                                        List[Dict[str,
                                                                  Logprob]]]]]


def check_logprobs_close(
    *,
    outputs_0_lst: Sequence[Union[TokensTextLogprobs, TextTextLogprobs]],
    outputs_1_lst: Sequence[Union[TokensTextLogprobs, TextTextLogprobs]],
    name_0: str,
    name_1: str,
    num_outputs_0_skip_tokens: int = 0,
    warn_on_mismatch: bool = True,
    always_check_logprobs: bool = False,
) -> None:
    """Compare the logprobs of two sequences generated by different models,
    which should be similar but not necessarily equal.

    Args:
      outputs_0_lst: First sequence to compare
      outputs_0_lst: Second sequence to compare
      name_0: sequence #0 name
      name_1: sequence #1 name
      num_outputs_0_skip_tokens: If > 0, specifies the number of initial
                                 sequence #0 tokens & logprobs to discard
                                 before comparison, i.e. all
                                 of sequence #1 will be compared to
                                 sequence #0 beginning at index
                                 num_outputs_0_skip_tokens
      warn_on_mismatch: Issue a warning if there is token-wise or text-wise
                        mismatch between the two sequences
      always_check_logprobs: If true, check logprobs even when tokens match
    """
    assert len(outputs_0_lst) == len(outputs_1_lst)

    # Loop through responses to each prompt.
    for prompt_idx, (outputs_0,
                     outputs_1) in enumerate(zip(outputs_0_lst,
                                                 outputs_1_lst)):
        output_ids_0, output_str_0, logprobs_0 = outputs_0
        output_ids_1, output_str_1, logprobs_1 = outputs_1

        if logprobs_0 is None:
            logprobs_0 = [None] * len(output_ids_0)
        if logprobs_1 is None:
            logprobs_1 = [None] * len(output_ids_1)

        # Skip specified number of initial sequence #0 tokens
        # & logprobs, leaving output text as-is for simplicity
        # (text mismatches may generate warnings but do not
        # cause the test to fail.)
        if num_outputs_0_skip_tokens < 0:
            raise ValueError("num_outputs_0_skip_tokens must be non-negative")
        output_ids_0 = output_ids_0[num_outputs_0_skip_tokens:]
        logprobs_0 = logprobs_0[num_outputs_0_skip_tokens:]

        # Loop through generated tokens.
        for idx, (output_id_0,
                  output_id_1) in enumerate(zip(output_ids_0, output_ids_1)):

            is_tok_mismatch = output_id_0 != output_id_1

            # If generated tokens don't match
            # or it is desired to always check logprobs,
            # then
            if is_tok_mismatch or always_check_logprobs:
                logprobs_elem_0 = logprobs_0[idx]
                logprobs_elem_1 = logprobs_1[idx]

                # Each predicted token must be in top N logprobs of the other
                fail_msg = (
                    f"Test{prompt_idx}:"
                    f"\nMatched tokens:\t{output_ids_0[:idx]}"
                    f"\n{name_0}:\t{output_str_0!r}\t{logprobs_elem_0}"
                    f"\n{name_1}:\t{output_str_1!r}\t{logprobs_elem_1}")

                assert logprobs_elem_0 is not None, fail_msg
                assert logprobs_elem_1 is not None, fail_msg
                assert output_id_0 in logprobs_elem_1, fail_msg
                assert output_id_1 in logprobs_elem_0, fail_msg

                if warn_on_mismatch and is_tok_mismatch:
                    with warnings.catch_warnings():
                        # This ensures that repeated warnings are shown
                        # in the output, not just the first occurrence
                        warnings.simplefilter("always")

                        warnings.warn(fail_msg, stacklevel=2)

                # Break out since sequences will now diverge.
                break
        else:
            if output_str_0 != output_str_1 and warn_on_mismatch:
                # The token outputs exactly match,
                # so the text outputs should exactly match as well
                fail_msg = (f"Test{prompt_idx}:"
                            f"\n{name_0}:\t{output_str_0!r}"
                            f"\n{name_1}:\t{output_str_1!r}")

                with warnings.catch_warnings():
                    # This ensures that repeated warnings are shown
                    # in the output, not just the first occurrence
                    warnings.simplefilter("always")

                    warnings.warn(fail_msg, stacklevel=2)

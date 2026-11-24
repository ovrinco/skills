class ListNode:
    def __init__(self, val=0, nxt=None):
        self.val, self.next = val, nxt


def merge(a, b):
    dummy_head = ListNode()
    tail = dummy_head
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy_head.next

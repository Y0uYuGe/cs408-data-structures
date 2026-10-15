/* C11 fundamentals: struct, pointer-to-pointer, allocation, deletion, and cleanup. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct Node { int value; struct Node* next; } Node;
static int push(Node** head, int value) {
    Node* node = malloc(sizeof *node);
    if (!node) return 0;
    node->value = value; node->next = *head; *head = node;
    return 1;
}
static int erase(Node** head, int value) {
    Node** cursor = head;
    while (*cursor) {
        if ((*cursor)->value == value) {
            Node* victim = *cursor; *cursor = victim->next; free(victim); return 1;
        }
        cursor = &(*cursor)->next;
    }
    return 0;
}
int main(void) {
    Node* head = NULL;
    assert(push(&head, 1)); assert(push(&head, 2)); assert(push(&head, 3));
    assert(erase(&head, 3)); assert(erase(&head, 1));
    assert(head->value == 2 && head->next == NULL);
    assert(erase(&head, 2)); assert(head == NULL); assert(!erase(&head, 9));
    puts("C11 pointer and lifecycle assertions passed");
    return 0;
}

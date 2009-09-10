from django import template

register = template.Library()

@register.filter
def partition_horizontal(thelist, n):
    n = int(n)
    return [thelist[i:i+n] for i in xrange(0, len(thelist), n)]

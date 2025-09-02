
from django.shortcuts import render

from .models import News

def news_list(request):
	news = News.objects.all().order_by('-date')
	news_with_source = []
	import re
	url_pattern = re.compile(r'(https?://\S+)')
	for n in news:
		match = url_pattern.search(n.body)
		source_url = match.group(1) if match else None
		news_with_source.append({
			'headline': n.headline,
			'body': n.body,
			'date': n.date,
			'source_url': source_url
		})
	return render(request, 'news.html', {'news': news_with_source})

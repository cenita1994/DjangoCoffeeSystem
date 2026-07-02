from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from audittrail.utils import log_audit
from .services import answer_menu_question


@login_required
def menu_assistant(request):
    chat_history = request.session.get('menu_assistant_chat_history', [])

    if request.method == 'POST':
        if request.POST.get('clear_chat') == '1':
            request.session['menu_assistant_chat_history'] = []
            request.session.modified = True
            return redirect('menu_assistant')

        question = request.POST.get('question', '').strip()

        if question:
            answer = answer_menu_question(question)

            chat_history.append({'sender': 'user', 'message': question})
            chat_history.append({'sender': 'assistant', 'message': answer})

            chat_history = chat_history[-20:]

            request.session['menu_assistant_chat_history'] = chat_history
            request.session.modified = True

            log_audit(
                request=request,
                action='Search',
                module='Smart Assistant',
                description=f'Asked Smart Assistant: {question[:150]}.',
                object_type='Chatbot Query',
                object_repr='Smart Assistant'
            )

        return redirect('menu_assistant')

    return render(request, 'menuassistant/menu_assistant.html', {
        'chat_history': chat_history,
    })


@login_required
def menu_assistant_history_api(request):
    chat_history = request.session.get('menu_assistant_chat_history', [])

    return JsonResponse({
        'success': True,
        'chat_history': chat_history,
    })


@login_required
@require_POST
def menu_assistant_api(request):
    question = request.POST.get('question', '').strip()

    if not question:
        return JsonResponse({
            'success': False,
            'answer': 'Please type a question first.'
        })

    answer = answer_menu_question(question)

    chat_history = request.session.get('menu_assistant_chat_history', [])

    chat_history.append({'sender': 'user', 'message': question})
    chat_history.append({'sender': 'assistant', 'message': answer})

    chat_history = chat_history[-20:]

    request.session['menu_assistant_chat_history'] = chat_history
    request.session.modified = True

    log_audit(
        request=request,
        action='Search',
        module='Smart Assistant',
        description=f'Asked Smart Assistant through floating chat: {question[:150]}.',
        object_type='Chatbot Query',
        object_repr='Smart Assistant'
    )

    return JsonResponse({
        'success': True,
        'question': question,
        'answer': answer,
    })


@login_required
@require_POST
def clear_menu_assistant_api(request):
    request.session['menu_assistant_chat_history'] = []
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'message': 'Chat cleared.'
    })

As mensagens vão para o terminal pelo `RichHandler` do `rich`. Para que o
tableau (veja `simplex.display`) apareça colorido no terminal e, ao mesmo
tempo, legível num arquivo de log, o `simplex.solver.Solver` registra o
título e o tableau em texto puro como mensagem e o tableau colorido (um
`rich.text.Text`) no atributo `RICH_TEXT` do registro (com `extra=`).

O `Handler` deste módulo mostra só a primeira linha da mensagem (o título)
na linha de log e o tableau colorido logo abaixo, fora da coluna de
mensagens do `RichHandler` e sem quebra de linha, para que um tableau
largo não seja picotado (alargue o terminal para vê-lo inteiro). Os
demais handlers (por exemplo, o arquivo de log do pytest) usam a mensagem
pura.

`configure_logging` põe o logger raiz no nível DEBUG se `debug`, senão
INFO, e acrescenta um `Handler` para o terminal (só se ainda não houver
um). Com `debug`, o `simplex.solver.Solver` mostra o tableau de cada
iteração da Fase 2. Os tableaux da Fase 1 (logger `PHASE_ONE_LOGGER`) só
aparecem se `phase_one` também for verdadeiro.

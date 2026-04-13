import base64

from pyteal import (
    App,
    Approve,
    Assert,
    Btoi,
    Bytes,
    Cond,
    Global,
    InnerTxnBuilder,
    Int,
    Mode,
    OnComplete,
    Gtxn,
    Seq,
    Txn,
    TxnField,
    TxnType,
    compileTeal,
)
from services.algorand_client import algod_client


def approval_program():
    creator_key = Bytes("creator")
    budget_key = Bytes("budget")
    app_reserve_key = Bytes("app_reserve")
    locked_key = Bytes("locked")
    released_key = Bytes("released")
    receiver_key = Bytes("receiver")
    trip_id_key = Bytes("trip_id")
    deadline_key = Bytes("deadline")
    status_key = Bytes("status")

    on_create = Seq(
        Assert(Txn.application_args.length() == Int(5)),
        App.globalPut(creator_key, Txn.sender()),
        App.globalPut(budget_key, Btoi(Txn.application_args[0])),
        App.globalPut(receiver_key, Txn.application_args[1]),
        App.globalPut(trip_id_key, Txn.application_args[2]),
        App.globalPut(deadline_key, Btoi(Txn.application_args[3])),
        App.globalPut(app_reserve_key, Btoi(Txn.application_args[4])),
        App.globalPut(locked_key, Int(0)),
        App.globalPut(released_key, Int(0)),
        App.globalPut(status_key, Int(0)),
        Approve(),
    )

    on_lock = Seq(
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(Txn.group_index() == Int(1)),
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].sender() == Txn.sender()),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),
        Assert(Gtxn[0].amount() == App.globalGet(budget_key) + App.globalGet(app_reserve_key)),
        Assert(App.globalGet(status_key) == Int(0)),
        App.globalPut(locked_key, Gtxn[0].amount()),
        App.globalPut(status_key, Int(1)),
        Approve(),
    )

    on_release = Seq(
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(App.globalGet(status_key) == Int(1)),
        Assert(App.globalGet(locked_key) >= App.globalGet(budget_key) + App.globalGet(app_reserve_key)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: App.globalGet(receiver_key),
            TxnField.amount: App.globalGet(budget_key),
            TxnField.fee: Int(0),
        }),
        InnerTxnBuilder.Submit(),
        App.globalPut(locked_key, App.globalGet(locked_key) - App.globalGet(budget_key)),
        App.globalPut(released_key, App.globalGet(budget_key)),
        App.globalPut(status_key, Int(2)),
        Approve(),
    )

    on_refund = Seq(
        Assert(Txn.sender() == App.globalGet(creator_key)),
        Assert(App.globalGet(status_key) == Int(1)),
        Assert(Global.latest_timestamp() >= App.globalGet(deadline_key)),
        Assert(App.globalGet(locked_key) >= App.globalGet(budget_key) + App.globalGet(app_reserve_key)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.receiver: App.globalGet(creator_key),
            TxnField.amount: App.globalGet(budget_key),
            TxnField.fee: Int(0),
        }),
        InnerTxnBuilder.Submit(),
        App.globalPut(locked_key, App.globalGet(locked_key) - App.globalGet(budget_key)),
        App.globalPut(released_key, Int(0)),
        App.globalPut(status_key, Int(3)),
        Approve(),
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, Cond(
            [Txn.application_args[0] == Bytes("lock"), on_lock],
            [Txn.application_args[0] == Bytes("release"), on_release],
            [Txn.application_args[0] == Bytes("refund"), on_refund],
        )],
    )

    return compileTeal(program, mode=Mode.Application, version=8)


def clear_program():
    return compileTeal(Approve(), mode=Mode.Application, version=8)


def compile_program(source_code):
    try:
        compile_response = algod_client.compile(source_code)
        return base64.b64decode(compile_response["result"])
    except Exception as exc:
        raise RuntimeError(f"Failed to compile TEAL program: {exc}") from exc